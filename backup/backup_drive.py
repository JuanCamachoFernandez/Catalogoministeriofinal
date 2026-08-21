import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from urllib.request import Request as UrlRequest, urlopen
from urllib.parse import urlsplit, unquote, parse_qs

import cloudinary
import cloudinary.api
import cloudinary.utils
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


SCOPES = ["https://www.googleapis.com/auth/drive.file"]
TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "/secrets/google-drive-token.json")
FOLDER_NAME = os.getenv("GOOGLE_DRIVE_FOLDER_NAME", "Backups Catalogo Ministerio")
POSTGRES_URI = os.environ.get("POSTGRES_URI")
CLOUDINARY_NAMESPACE = os.getenv("CLOUDINARY_BACKUP_PREFIX", "catalogo-ministerio").strip("/")
CLOUDINARY_RESOURCE_TYPES = tuple(
    item.strip()
    for item in os.getenv("CLOUDINARY_RESOURCE_TYPES", "image,video,raw").split(",")
    if item.strip()
)
CLOUDINARY_DELIVERY_TYPES = tuple(
    item.strip()
    for item in os.getenv(
        "CLOUDINARY_DELIVERY_TYPES", "upload,private,authenticated"
    ).split(",")
    if item.strip()
)
MAX_STATES = 2
DRIVE_PAGE_SIZE = 1000
CLOUDINARY_PAGE_SIZE = 500
TRANSFER_CHUNK_SIZE = 5 * 1024 * 1024
DOWNLOAD_CHUNK_SIZE = 1024 * 1024
MANIFEST_SCHEMA_VERSION = 1
DATABASE_ASSET_REFERENCES = (
    {
        "table": "usuarios",
        "url_column": "foto_perfil",
        "public_id_column": "identificador_foto_cloudinary",
    },
    {
        "table": "expositores",
        "url_column": "logo",
        "public_id_column": "identificador_logo_cloudinary",
    },
    {
        "table": "ferias",
        "url_column": "imagen_portada",
        "public_id_column": "identificador_portada_cloudinary",
    },
    {
        "table": "solicitudes_registro",
        "url_column": "logo_url",
        "public_id_column": "identificador_logo_cloudinary",
    },
    {
        "table": "unidades_productivas",
        "url_column": "logo_url",
        "public_id_column": "identificador_logo_cloudinary",
    },
    {
        "table": "imagenes_producto",
        "url_column": "direccion_url",
        "public_id_column": "identificador_cloudinary",
    },
    {
        "table": "productos_solicitud_registro",
        "url_column": "imagen_url",
        "public_id_column": None,
    },
)


def utc_now():
    return datetime.now(timezone.utc)


def log(scope, message):
    print(f"[{scope}] {message}", flush=True)


def secret_values():
    names = (
        "POSTGRES_URI",
        "CLOUDINARY_URL",
        "CLOUDINARY_API_KEY",
        "CLOUDINARY_API_SECRET",
    )
    return [os.getenv(name) for name in names if os.getenv(name)]


def safe_error(error):
    message = f"{type(error).__name__}: {error}"
    for secret in secret_values():
        message = message.replace(secret, "[REDACTED]")
    return message


def escapar_drive(texto):
    return texto.replace("\\", "\\\\").replace("'", "\\'")


def obtener_drive():
    if not os.path.exists(TOKEN_PATH):
        raise RuntimeError(f"No existe el archivo de credenciales en {TOKEN_PATH}")

    credenciales = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if credenciales.expired and credenciales.refresh_token:
        credenciales.refresh(Request())
    if not credenciales.valid:
        raise RuntimeError("Las credenciales de Google Drive no son validas")

    return build("drive", "v3", credentials=credenciales, cache_discovery=False)


def configurar_cloudinary():
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    cloudinary_url = os.getenv("CLOUDINARY_URL")

    if all((cloud_name, api_key, api_secret)):
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True,
        )
    elif cloudinary_url:
        # El SDK lee CLOUDINARY_URL directamente. No se registra su contenido.
        cloudinary.config(secure=True)
    else:
        raise RuntimeError(
            "Faltan CLOUDINARY_CLOUD_NAME/CLOUDINARY_API_KEY/"
            "CLOUDINARY_API_SECRET o CLOUDINARY_URL"
        )

    config = cloudinary.config()
    if not all((config.cloud_name, config.api_key, config.api_secret)):
        raise RuntimeError("La configuracion de Cloudinary esta incompleta")
    return config


def iterar_archivos_drive(drive, folder_id):
    if not folder_id:
        return
    page_token = None
    while True:
        response = (
            drive.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false",
                spaces="drive",
                fields=(
                    "nextPageToken,files(id,name,mimeType,createdTime,modifiedTime,"
                    "size,md5Checksum,appProperties)"
                ),
                pageSize=DRIVE_PAGE_SIZE,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        yield from response.get("files", [])
        page_token = response.get("nextPageToken")
        if not page_token:
            break


def buscar_carpeta(drive, nombre, parent_id=None):
    escaped_name = escapar_drive(nombre)
    clauses = [
        "mimeType = 'application/vnd.google-apps.folder'",
        f"name = '{escaped_name}'",
        "trashed = false",
    ]
    if parent_id:
        clauses.append(f"'{parent_id}' in parents")

    page_token = None
    while True:
        response = (
            drive.files()
            .list(
                q=" and ".join(clauses),
                spaces="drive",
                fields="nextPageToken,files(id,name,createdTime)",
                pageSize=100,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        files = response.get("files", [])
        if files:
            files.sort(key=lambda item: item.get("createdTime", ""))
            return files[0]
        page_token = response.get("nextPageToken")
        if not page_token:
            return None


def obtener_o_crear_carpeta(drive, nombre, parent_id=None, dry_run=False):
    folder = buscar_carpeta(drive, nombre, parent_id)
    if folder:
        return folder["id"]
    if dry_run:
        log("DRY-RUN", f"Se crearia la carpeta Drive: {nombre}")
        return None

    metadata = {
        "name": nombre,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]
    folder = (
        drive.files()
        .create(body=metadata, fields="id,name", supportsAllDrives=True)
        .execute()
    )
    return folder["id"]


def normalizar_postgres_uri(uri):
    if not uri:
        return uri
    return uri.replace("postgresql+psycopg://", "postgresql://", 1)


def crear_dump(ruta):
    if not POSTGRES_URI:
        raise RuntimeError("Falta POSTGRES_URI")

    uri = normalizar_postgres_uri(POSTGRES_URI)

    parsed = urlsplit(uri)

    if parsed.scheme not in ("postgresql", "postgres"):
        raise RuntimeError(
            "POSTGRES_URI no tiene un formato PostgreSQL valido"
        )

    if not parsed.hostname:
        raise RuntimeError(
            "POSTGRES_URI no contiene HOST"
        )

    if not parsed.username:
        raise RuntimeError(
            "POSTGRES_URI no contiene USERNAME"
        )

    database = parsed.path.lstrip("/")

    if not database:
        raise RuntimeError(
            "POSTGRES_URI no contiene DATABASE"
        )

    pg_env = os.environ.copy()

    pg_env["PGHOST"] = parsed.hostname
    pg_env["PGPORT"] = str(parsed.port or 5432)
    pg_env["PGUSER"] = unquote(parsed.username)
    pg_env["PGDATABASE"] = unquote(database)

    if parsed.password:
        pg_env["PGPASSWORD"] = unquote(
            parsed.password
        )

    query = parse_qs(parsed.query)

    if query.get("sslmode"):
        pg_env["PGSSLMODE"] = query["sslmode"][0]

    log(
        "DB",
        "Conexion PostgreSQL preparada mediante variables PG*"
    )

    command = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-acl",
        "--file",
        ruta,
    ]

    subprocess.run(
        command,
        check=True,
        env=pg_env,
    )

    if (
        not os.path.exists(ruta)
        or os.path.getsize(ruta) == 0
    ):
        raise RuntimeError(
            "El dump PostgreSQL se creo vacio"
        )

    subprocess.run(
        [
            "pg_restore",
            "--list",
            ruta,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    log(
        "DB",
        "Backup PostgreSQL OK"
    )


def subir_archivo(
    drive,
    folder_id,
    ruta,
    nombre,
    mimetype,
    app_properties=None,
):
    metadata = {"name": nombre, "parents": [folder_id]}
    if app_properties:
        metadata["appProperties"] = {
            str(key): str(value)[:124]
            for key, value in app_properties.items()
            if value is not None
        }
    media = MediaFileUpload(
        ruta,
        mimetype=mimetype,
        resumable=True,
        chunksize=TRANSFER_CHUNK_SIZE,
    )
    request = drive.files().create(
        body=metadata,
        media_body=media,
        fields="id,name,createdTime,size,md5Checksum,appProperties",
        supportsAllDrives=True,
    )
    response = None
    while response is None:
        _status, response = request.next_chunk()
    return response


def verificar_subida_drive(uploaded, expected_size, expected_md5):
    if int(uploaded.get("size", -1)) != int(expected_size):
        raise RuntimeError("Google Drive informo un tamano diferente al archivo local")
    drive_md5 = uploaded.get("md5Checksum")
    if not drive_md5:
        raise RuntimeError("Google Drive no devolvio checksum MD5 del archivo subido")
    if drive_md5.lower() != expected_md5.lower():
        raise RuntimeError("Google Drive informo un checksum diferente al archivo local")


def pertenece_al_namespace(asset):
    prefix = f"{CLOUDINARY_NAMESPACE}/"
    public_id = (asset.get("public_id") or "").lstrip("/")
    asset_folder = (asset.get("asset_folder") or asset.get("folder") or "").strip("/")
    return (
        public_id == CLOUDINARY_NAMESPACE
        or public_id.startswith(prefix)
        or asset_folder == CLOUDINARY_NAMESPACE
        or asset_folder.startswith(prefix)
    )


def iterar_assets_cloudinary():
    seen_asset_ids = set()
    for resource_type in CLOUDINARY_RESOURCE_TYPES:
        for delivery_type in CLOUDINARY_DELIVERY_TYPES:
            cursor = None
            while True:
                options = {
                    "resource_type": resource_type,
                    "type": delivery_type,
                    "max_results": CLOUDINARY_PAGE_SIZE,
                }
                if cursor:
                    options["next_cursor"] = cursor
                response = cloudinary.api.resources(**options)
                for asset in response.get("resources", []):
                    if not pertenece_al_namespace(asset):
                        continue
                    asset_id = asset.get("asset_id")
                    dedupe_id = asset_id or (
                        f"{resource_type}:{delivery_type}:{asset.get('public_id')}"
                    )
                    if dedupe_id in seen_asset_ids:
                        continue
                    seen_asset_ids.add(dedupe_id)
                    asset.setdefault("resource_type", resource_type)
                    asset.setdefault("type", delivery_type)
                    yield asset
                cursor = response.get("next_cursor")
                if not cursor:
                    break


def source_checksum(asset):
    for field in ("etag", "checksum", "md5", "sha1"):
        if asset.get(field):
            return {"algorithm": field, "value": str(asset[field])}
    return None


def media_backup_key(asset):
    identity = {
        "asset_id": asset.get("asset_id") or f"public_id:{asset.get('public_id')}",
        "resource_type": asset.get("resource_type"),
        "type": asset.get("type"),
        "format": asset.get("format"),
        "bytes": asset.get("bytes"),
        "version": asset.get("version"),
        "source_checksum": source_checksum(asset),
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def nombre_media(asset, backup_key):
    asset_id = re.sub(r"[^A-Za-z0-9_-]+", "_", str(asset.get("asset_id") or "asset"))
    asset_id = asset_id[:64] or "asset"
    extension = re.sub(r"[^A-Za-z0-9]+", "", str(asset.get("format") or "bin"))
    extension = extension.lower()[:12] or "bin"
    return f"cloudinary_{asset_id}_{backup_key[:16]}.{extension}"


def url_descarga_asset(asset):
    if asset.get("type", "upload") == "upload" and asset.get("secure_url"):
        return asset["secure_url"]
    url, _options = cloudinary.utils.cloudinary_url(
        asset["public_id"],
        resource_type=asset.get("resource_type", "image"),
        type=asset.get("type", "upload"),
        format=asset.get("format"),
        version=asset.get("version"),
        secure=True,
        sign_url=True,
    )
    return url


def descargar_asset(asset, target_path):
    request = UrlRequest(
        url_descarga_asset(asset),
        headers={"User-Agent": "catalogo-ministerio-backup/1.0"},
    )
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    total = 0
    with urlopen(request, timeout=120) as response, open(target_path, "wb") as output:
        status = getattr(response, "status", 200)
        if status != 200:
            raise RuntimeError(f"Cloudinary respondio HTTP {status}")
        while True:
            chunk = response.read(DOWNLOAD_CHUNK_SIZE)
            if not chunk:
                break
            output.write(chunk)
            sha256.update(chunk)
            md5.update(chunk)
            total += len(chunk)

    expected_size = asset.get("bytes")
    if total == 0:
        raise RuntimeError("Cloudinary devolvio un asset vacio")
    if expected_size is not None and total != int(expected_size):
        raise RuntimeError(
            f"Tamano descargado distinto para asset_id={asset.get('asset_id')}"
        )
    return {"bytes": total, "sha256": sha256.hexdigest(), "md5": md5.hexdigest()}


def indexar_media_drive(drive, media_folder_id):
    indexed = {}
    for item in iterar_archivos_drive(drive, media_folder_id):
        backup_key = (item.get("appProperties") or {}).get("backupKey")
        if backup_key:
            indexed.setdefault(backup_key, item)
    return indexed


def media_reutilizable(drive_file, asset):
    if not drive_file:
        return False
    expected_size = asset.get("bytes")
    if expected_size is not None and int(drive_file.get("size", -1)) != int(expected_size):
        return False
    stored_md5 = (drive_file.get("appProperties") or {}).get("backupMd5")
    stored_sha256 = (drive_file.get("appProperties") or {}).get("backupSha256")
    drive_md5 = drive_file.get("md5Checksum")
    return bool(
        stored_md5
        and stored_sha256
        and drive_md5
        and stored_md5.lower() == drive_md5.lower()
    )


def manifest_asset(asset, drive_file, backup_key, hashes=None):
    properties = drive_file.get("appProperties") or {}
    backup_md5 = (hashes or {}).get("md5") or properties.get("backupMd5")
    backup_sha256 = (hashes or {}).get("sha256") or properties.get("backupSha256")
    return {
        "asset_id": asset.get("asset_id"),
        "public_id": asset.get("public_id"),
        "secure_url": asset.get("secure_url"),
        "resource_type": asset.get("resource_type"),
        "type": asset.get("type"),
        "format": asset.get("format"),
        "bytes": asset.get("bytes"),
        "version": asset.get("version"),
        "folder": asset.get("folder"),
        "asset_folder": asset.get("asset_folder"),
        "created_at": asset.get("created_at"),
        "checksum": source_checksum(asset),
        "google_drive_filename": drive_file.get("name"),
        "google_drive_file_id": drive_file.get("id"),
        "backup_key": backup_key,
        "backup_bytes": int(drive_file.get("size", asset.get("bytes") or 0)),
        "backup_md5": backup_md5,
        "backup_sha256": backup_sha256,
    }


def respaldar_media(drive, media_folder_id, temp_dir, dry_run=False):
    existing = indexar_media_drive(drive, media_folder_id) if media_folder_id else {}
    manifest_assets = []
    found = new = reused = errors = 0

    for asset in iterar_assets_cloudinary():
        found += 1
        backup_key = media_backup_key(asset)
        drive_file = existing.get(backup_key)
        if media_reutilizable(drive_file, asset):
            reused += 1
            manifest_assets.append(manifest_asset(asset, drive_file, backup_key))
            continue

        if dry_run:
            new += 1
            continue

        target = os.path.join(temp_dir, "cloudinary-asset.tmp")
        try:
            hashes = descargar_asset(asset, target)
            name = nombre_media(asset, backup_key)
            uploaded = subir_archivo(
                drive,
                media_folder_id,
                target,
                name,
                "application/octet-stream",
                app_properties={
                    "backupKey": backup_key,
                    "cloudinaryAssetId": asset.get("asset_id"),
                    "cloudinaryVersion": asset.get("version"),
                    "backupMd5": hashes["md5"],
                    "backupSha256": hashes["sha256"],
                },
            )
            verificar_subida_drive(uploaded, hashes["bytes"], hashes["md5"])
            existing[backup_key] = uploaded
            manifest_assets.append(
                manifest_asset(asset, uploaded, backup_key, hashes=hashes)
            )
            new += 1
        except Exception as error:
            errors += 1
            log(
                "MEDIA",
                f"Error en asset_id={asset.get('asset_id') or 'desconocido'}: "
                f"{safe_error(error)}",
            )
        finally:
            try:
                os.remove(target)
            except FileNotFoundError:
                pass

    log("CLOUDINARY", f"Assets encontrados: {found}")
    log("MEDIA", f"Nuevos: {new}")
    log("MEDIA", f"Ya respaldados: {reused}")
    log("MEDIA", f"Errores: {errors}")
    if errors:
        raise RuntimeError(
            "El backup de media quedo incompleto; no se publicara un nuevo manifest"
        )
    return manifest_assets, {"found": found, "new": new, "reused": reused, "errors": errors}


def hash_file(path):
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    size = 0
    with open(path, "rb") as source:
        while True:
            chunk = source.read(DOWNLOAD_CHUNK_SIZE)
            if not chunk:
                break
            sha256.update(chunk)
            md5.update(chunk)
            size += len(chunk)
    return {"bytes": size, "sha256": sha256.hexdigest(), "md5": md5.hexdigest()}


def crear_manifest(state_id, created_at, database_file, database_hashes, assets, summary, cloud_name):
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "state_id": state_id,
        "created_at": created_at,
        "complete": True,
        "database": {
            "google_drive_file_id": database_file["id"],
            "google_drive_filename": database_file["name"],
            "bytes": int(database_file.get("size", database_hashes["bytes"])),
            "md5": database_file.get("md5Checksum") or database_hashes["md5"],
            "sha256": database_hashes["sha256"],
            "format": "postgresql-custom",
            "validated_with": "pg_restore --list",
        },
        "cloudinary": {
            "cloud_name": cloud_name,
            "namespace": CLOUDINARY_NAMESPACE,
            "resource_types": list(CLOUDINARY_RESOURCE_TYPES),
            "delivery_types": list(CLOUDINARY_DELIVERY_TYPES),
        },
        "assets": assets,
        "summary": summary,
        "restore": {
            "order": ["cloudinary", "postgresql"],
            "database_asset_references": list(DATABASE_ASSET_REFERENCES),
            "cloudinary": (
                "Upload each media file with its original public_id, resource_type, "
                "type, format and overwrite=true; record the new secure_url/version and "
                "verify bytes/checksums before use."
            ),
            "postgresql": (
                "Validate with pg_restore --list, restore into an empty target database, "
                "then replace old secure URLs with the URLs returned by the Cloudinary "
                "restore while preserving public IDs."
            ),
        },
    }


def guardar_manifest_local(manifest, path):
    with open(path, "w", encoding="utf-8") as output:
        json.dump(manifest, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def descargar_json_drive(drive, file_id, temp_dir):
    path = os.path.join(temp_dir, f"manifest-{file_id}.json")
    request = drive.files().get_media(fileId=file_id, supportsAllDrives=True)
    with open(path, "wb") as output:
        downloader = MediaIoBaseDownload(output, request, chunksize=TRANSFER_CHUNK_SIZE)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
    with open(path, encoding="utf-8") as source:
        return json.load(source)


def enviar_a_papelera(drive, file_id):
    drive.files().update(
        fileId=file_id,
        body={"trashed": True},
        fields="id,trashed",
        supportsAllDrives=True,
    ).execute()


def aplicar_retencion(drive, folders, current_manifest, current_manifest_file, temp_dir):
    manifests = list(iterar_archivos_drive(drive, folders["manifests"]))
    manifests = [item for item in manifests if item.get("name", "").endswith(".json")]
    manifests.sort(key=lambda item: item.get("createdTime", ""), reverse=True)
    current = next(
        (item for item in manifests if item["id"] == current_manifest_file["id"]),
        current_manifest_file,
    )
    # El estado recién publicado siempre se conserva, incluso si Drive devuelve
    # una fecha inesperada por desfase de reloj o metadatos migrados.
    kept = [current]
    kept.extend(
        item
        for item in manifests
        if item["id"] != current["id"]
    )
    kept = kept[:MAX_STATES]
    kept_ids = {item["id"] for item in kept}
    old = [item for item in manifests if item["id"] not in kept_ids]

    database_refs = set()
    media_refs = set()
    for item in kept:
        if item["id"] == current_manifest_file["id"]:
            manifest = current_manifest
        else:
            manifest = descargar_json_drive(drive, item["id"], temp_dir)
        if not manifest.get("complete") or not manifest.get("database"):
            raise RuntimeError("Manifest conservado invalido; retencion cancelada")
        database_refs.add(manifest["database"]["google_drive_file_id"])
        for asset in manifest.get("assets", []):
            file_id = asset.get("google_drive_file_id")
            if file_id:
                media_refs.add(file_id)

    # Solo se modifica Drive después de validar completamente ambos estados.
    for item in old:
        enviar_a_papelera(drive, item["id"])
    for item in iterar_archivos_drive(drive, folders["database"]):
        if item["id"] not in database_refs:
            enviar_a_papelera(drive, item["id"])
    for item in iterar_archivos_drive(drive, folders["media"]):
        if item["id"] not in media_refs:
            enviar_a_papelera(drive, item["id"])

    log("RETENTION", f"Estados conservados: {len(kept)}")


def preparar_carpetas(drive, dry_run=False):
    root = obtener_o_crear_carpeta(drive, FOLDER_NAME, dry_run=dry_run)
    return {
        "root": root,
        "database": obtener_o_crear_carpeta(
            drive, "database", root, dry_run=dry_run
        ) if root else None,
        "manifests": obtener_o_crear_carpeta(
            drive, "manifests", root, dry_run=dry_run
        ) if root else None,
        "media": obtener_o_crear_carpeta(
            drive, "media", root, dry_run=dry_run
        ) if root else None,
    }


def ejecutar_backup(dry_run=False):
    timestamp = utc_now()
    state_id = timestamp.strftime("%Y-%m-%d_%H-%M-%S_UTC")
    log("BACKUP", "Inicio de respaldo integral")

    cloudinary_config = configurar_cloudinary()
    drive = obtener_drive()
    folders = preparar_carpetas(drive, dry_run=dry_run)

    with tempfile.TemporaryDirectory() as temp_dir:
        dump_name = f"catalogo_{state_id}.dump"
        dump_path = os.path.join(temp_dir, dump_name)
        if not dry_run:
            # El snapshot SQL ocurre antes del inventario: si la media cambia
            # después, la validación por versión/tamaño falla en vez de publicar
            # un estado que no corresponda al dump.
            crear_dump(dump_path)

        assets, summary = respaldar_media(
            drive, folders["media"], temp_dir, dry_run=dry_run
        )
        if dry_run:
            log("DB", "Dry-run: pg_dump no ejecutado")
            log("MANIFEST", "Se crearia correctamente")
            log("RETENTION", f"Estados conservados: {MAX_STATES} (sin cambios)")
            log("BACKUP", "DRY-RUN COMPLETADO CORRECTAMENTE")
            return

        if not all((folders["database"], folders["manifests"], folders["media"])):
            raise RuntimeError("No fue posible preparar la estructura de Google Drive")

        database_hashes = hash_file(dump_path)
        database_file = subir_archivo(
            drive,
            folders["database"],
            dump_path,
            dump_name,
            "application/octet-stream",
            app_properties={"stateId": state_id, "kind": "postgresql"},
        )
        verificar_subida_drive(
            database_file, database_hashes["bytes"], database_hashes["md5"]
        )

        manifest = crear_manifest(
            state_id,
            timestamp.isoformat(),
            database_file,
            database_hashes,
            assets,
            summary,
            cloudinary_config.cloud_name,
        )
        manifest_name = f"catalogo_{state_id}.manifest.json"
        manifest_path = os.path.join(temp_dir, manifest_name)
        guardar_manifest_local(manifest, manifest_path)
        manifest_hashes = hash_file(manifest_path)
        manifest_file = subir_archivo(
            drive,
            folders["manifests"],
            manifest_path,
            manifest_name,
            "application/json",
            app_properties={
                "stateId": state_id,
                "kind": "manifest",
                "backupSha256": manifest_hashes["sha256"],
            },
        )
        verificar_subida_drive(
            manifest_file, manifest_hashes["bytes"], manifest_hashes["md5"]
        )
        log("MANIFEST", "Creado correctamente")

        aplicar_retencion(drive, folders, manifest, manifest_file, temp_dir)

    log("BACKUP", "COMPLETADO CORRECTAMENTE")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Respalda PostgreSQL y Cloudinary en Google Drive"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.getenv("BACKUP_DRY_RUN", "false").lower() == "true",
        help="Inventaria y planifica sin escribir en Drive ni ejecutar pg_dump",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    ejecutar_backup(dry_run=args.dry_run)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        log("BACKUP", f"ERROR: {safe_error(error)}")
        raise SystemExit(1)
