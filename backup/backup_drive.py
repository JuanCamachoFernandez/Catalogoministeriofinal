import os
import subprocess
import tempfile
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


SCOPES = [
    "https://www.googleapis.com/auth/drive.file"
]

TOKEN_PATH = os.getenv(
    "GOOGLE_TOKEN_PATH",
    "/secrets/google-drive-token.json",
)

FOLDER_NAME = os.getenv(
    "GOOGLE_DRIVE_FOLDER_NAME",
    "Backups Catalogo Ministerio",
)

MAX_BACKUPS = int(
    os.getenv("MAX_BACKUPS", "2")
)

POSTGRES_URI = os.environ.get(
    "POSTGRES_URI"
)


def escapar_drive(texto):
    return (
        texto
        .replace("\\", "\\\\")
        .replace("'", "\\'")
    )


def obtener_drive():
    if not os.path.exists(TOKEN_PATH):
        raise RuntimeError(
            f"No existe {TOKEN_PATH}"
        )

    credenciales = (
        Credentials.from_authorized_user_file(
            TOKEN_PATH,
            SCOPES,
        )
    )

    if (
        credenciales.expired
        and credenciales.refresh_token
    ):
        credenciales.refresh(Request())

    if not credenciales.valid:
        raise RuntimeError(
            "Las credenciales de Google Drive "
            "no son validas."
        )

    return build(
        "drive",
        "v3",
        credentials=credenciales,
        cache_discovery=False,
    )


def obtener_o_crear_carpeta(drive):
    nombre = escapar_drive(
        FOLDER_NAME
    )

    respuesta = (
        drive.files()
        .list(
            q=(
                "mimeType = "
                "'application/vnd.google-apps.folder' "
                f"and name = '{nombre}' "
                "and trashed = false"
            ),
            spaces="drive",
            fields="files(id,name)",
            pageSize=20,
        )
        .execute()
    )

    carpetas = respuesta.get(
        "files",
        [],
    )

    if carpetas:
        carpeta = carpetas[0]

        print(
            "Carpeta Drive encontrada:",
            carpeta["name"],
        )

        return carpeta["id"]

    carpeta = (
        drive.files()
        .create(
            body={
                "name": FOLDER_NAME,
                "mimeType":
                    "application/vnd.google-apps.folder",
            },
            fields="id,name",
        )
        .execute()
    )

    print(
        "Carpeta Drive creada:",
        carpeta["name"],
    )

    return carpeta["id"]


def crear_dump(ruta):
    if not POSTGRES_URI:
        raise RuntimeError(
            "Falta POSTGRES_URI."
        )

    print("Creando dump PostgreSQL...")

    comando = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-acl",
        "--file",
        ruta,
        "--dbname",
        POSTGRES_URI,
    ]

    subprocess.run(
        comando,
        check=True,
    )

    if (
        not os.path.exists(ruta)
        or os.path.getsize(ruta) == 0
    ):
        raise RuntimeError(
            "El dump se creo vacio."
        )

    print(
        "Dump creado:",
        os.path.getsize(ruta),
        "bytes",
    )

    print(
        "Verificando dump..."
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

    print(
        "Dump valido: OK"
    )


def subir_dump(
    drive,
    folder_id,
    ruta,
    nombre,
):
    metadata = {
        "name": nombre,
        "parents": [folder_id],
    }

    media = MediaFileUpload(
        ruta,
        mimetype="application/octet-stream",
        resumable=True,
        chunksize=5 * 1024 * 1024,
    )

    solicitud = (
        drive.files()
        .create(
            body=metadata,
            media_body=media,
            fields=(
                "id,name,createdTime,size"
            ),
        )
    )

    respuesta = None

    while respuesta is None:
        estado, respuesta = (
            solicitud.next_chunk()
        )

        if estado:
            porcentaje = int(
                estado.progress() * 100
            )
            print(
                f"Subiendo: {porcentaje}%"
            )

    print(
        "Backup subido a Drive:",
        respuesta["name"],
    )

    return respuesta


def rotar_backups(
    drive,
    folder_id,
):
    respuesta = (
        drive.files()
        .list(
            q=(
                f"'{folder_id}' in parents "
                "and trashed = false"
            ),
            spaces="drive",
            fields=(
                "files("
                "id,name,createdTime,size"
                ")"
            ),
            pageSize=100,
        )
        .execute()
    )

    backups = [
        archivo
        for archivo
        in respuesta.get(
            "files",
            [],
        )
        if archivo.get(
            "name",
            "",
        ).startswith("catalogo_")
        and archivo.get(
            "name",
            "",
        ).endswith(".dump")
    ]

    backups.sort(
        key=lambda archivo:
            archivo.get(
                "createdTime",
                "",
            ),
        reverse=True,
    )

    print(
        "Backups encontrados:",
        len(backups),
    )

    antiguos = backups[
        MAX_BACKUPS:
    ]

    for archivo in antiguos:
        drive.files().delete(
            fileId=archivo["id"]
        ).execute()

        print(
            "Backup antiguo eliminado:",
            archivo["name"],
        )

    print(
        "Backups conservados:",
        min(
            len(backups),
            MAX_BACKUPS,
        ),
    )


def main():
    fecha = datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d_%H-%M-%S_UTC"
    )

    nombre = (
        f"catalogo_{fecha}.dump"
    )

    print(
        "================================"
    )
    print(
        "BACKUP CATALOGO MINISTERIO"
    )
    print(
        "================================"
    )

    with tempfile.TemporaryDirectory() as temp:
        ruta = os.path.join(
            temp,
            nombre,
        )

        crear_dump(
            ruta
        )

        drive = obtener_drive()

        folder_id = (
            obtener_o_crear_carpeta(
                drive
            )
        )

        # IMPORTANTE:
        # la rotacion ocurre solamente
        # despues de una subida exitosa.
        subir_dump(
            drive,
            folder_id,
            ruta,
            nombre,
        )

        rotar_backups(
            drive,
            folder_id,
        )

    print(
        "================================"
    )
    print(
        "BACKUP TERMINADO: OK"
    )
    print(
        "================================"
    )


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print("")
        print(
            "BACKUP TERMINADO: ERROR"
        )
        print(
            type(error).__name__
            + ":",
            error,
        )

        raise