import hashlib
import importlib.util
import sys
import types
from pathlib import Path


def _module(name):
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


def _load_backup_module():
    cloudinary = _module("cloudinary")
    cloudinary.api = _module("cloudinary.api")
    cloudinary.utils = _module("cloudinary.utils")
    cloudinary.config = lambda **_kwargs: types.SimpleNamespace(
        cloud_name="test", api_key="key", api_secret="secret"
    )

    _module("google")
    _module("google.auth")
    _module("google.auth.transport")
    google_requests = _module("google.auth.transport.requests")
    google_requests.Request = object
    _module("google.oauth2")
    google_credentials = _module("google.oauth2.credentials")
    google_credentials.Credentials = object
    _module("googleapiclient")
    google_discovery = _module("googleapiclient.discovery")
    google_discovery.build = lambda *_args, **_kwargs: None
    google_http = _module("googleapiclient.http")
    google_http.MediaFileUpload = object
    google_http.MediaIoBaseDownload = object

    path = Path(__file__).with_name("backup_drive.py")
    spec = importlib.util.spec_from_file_location("backup_drive_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


backup = _load_backup_module()


def sample_asset(**overrides):
    asset = {
        "asset_id": "asset-1",
        "public_id": "catalogo-ministerio/productos/abc",
        "secure_url": "https://example.invalid/abc.webp",
        "resource_type": "image",
        "type": "upload",
        "format": "webp",
        "bytes": 4,
        "version": 10,
        "created_at": "2026-08-20T10:00:00Z",
        "etag": "source-etag",
    }
    asset.update(overrides)
    return asset


def test_cloudinary_inventory_is_paginated_and_filters_namespace(monkeypatch):
    calls = []

    def resources(**options):
        calls.append(options)
        if not options.get("next_cursor"):
            return {
                "resources": [
                    sample_asset(),
                    sample_asset(
                        asset_id="external",
                        public_id="otro-sistema/imagen",
                    ),
                ],
                "next_cursor": "page-2",
            }
        return {
            "resources": [
                sample_asset(
                    asset_id="dynamic-folder",
                    public_id="abc",
                    asset_folder="catalogo-ministerio/perfiles",
                )
            ]
        }

    monkeypatch.setattr(backup, "CLOUDINARY_RESOURCE_TYPES", ("image",))
    monkeypatch.setattr(backup, "CLOUDINARY_DELIVERY_TYPES", ("upload",))
    monkeypatch.setattr(backup.cloudinary.api, "resources", resources, raising=False)

    assets = list(backup.iterar_assets_cloudinary())

    assert [item["asset_id"] for item in assets] == ["asset-1", "dynamic-folder"]
    assert calls[0]["max_results"] == 500
    assert calls[1]["next_cursor"] == "page-2"


def test_backup_key_changes_with_asset_version_and_drive_copy_is_verified():
    original = sample_asset()
    changed = sample_asset(version=11)
    renamed = sample_asset(public_id="catalogo-ministerio/productos/renamed")
    original_key = backup.media_backup_key(original)

    assert original_key != backup.media_backup_key(changed)
    assert original_key == backup.media_backup_key(renamed)
    assert backup.media_reutilizable(
        {
            "size": "4",
            "md5Checksum": "abcd",
            "appProperties": {"backupMd5": "abcd", "backupSha256": "1234"},
        },
        original,
    )
    assert not backup.media_reutilizable(
        {
            "size": "4",
            "md5Checksum": "different",
            "appProperties": {"backupMd5": "abcd", "backupSha256": "1234"},
        },
        original,
    )


def test_download_streams_and_validates_hashes(tmp_path, monkeypatch):
    class Response:
        status = 200

        def __enter__(self):
            self.remaining = b"data"
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _size):
            chunk, self.remaining = self.remaining, b""
            return chunk

    monkeypatch.setattr(backup, "urlopen", lambda *_args, **_kwargs: Response())
    target = tmp_path / "asset.tmp"

    result = backup.descargar_asset(sample_asset(), target)

    assert target.read_bytes() == b"data"
    assert result["bytes"] == 4
    assert result["sha256"] == hashlib.sha256(b"data").hexdigest()


def test_retention_keeps_current_and_previous_references(monkeypatch, tmp_path):
    listings = {
        "manifests": [
            {"id": "future", "name": "future.json", "createdTime": "2099"},
            {"id": "current", "name": "current.json", "createdTime": "2026"},
            {"id": "old", "name": "old.json", "createdTime": "2025"},
        ],
        "database": [{"id": value} for value in ("db-current", "db-future", "db-old")],
        "media": [{"id": value} for value in ("media-current", "media-future", "media-old")],
    }
    current_manifest = {
        "complete": True,
        "database": {"google_drive_file_id": "db-current"},
        "assets": [{"google_drive_file_id": "media-current"}],
    }
    future_manifest = {
        "complete": True,
        "database": {"google_drive_file_id": "db-future"},
        "assets": [{"google_drive_file_id": "media-future"}],
    }
    trashed = []

    monkeypatch.setattr(
        backup,
        "iterar_archivos_drive",
        lambda _drive, folder_id: iter(listings[folder_id]),
    )
    monkeypatch.setattr(
        backup,
        "descargar_json_drive",
        lambda *_args: future_manifest,
    )
    monkeypatch.setattr(
        backup,
        "enviar_a_papelera",
        lambda _drive, file_id: trashed.append(file_id),
    )

    backup.aplicar_retencion(
        None,
        {"manifests": "manifests", "database": "database", "media": "media"},
        current_manifest,
        {"id": "current", "name": "current.json", "createdTime": "2026"},
        str(tmp_path),
    )

    assert set(trashed) == {"old", "db-old", "media-old"}


def test_manifest_contains_restore_and_required_asset_fields():
    asset = sample_asset(folder="catalogo-ministerio/productos")
    key = backup.media_backup_key(asset)
    item = backup.manifest_asset(
        asset,
        {
            "id": "drive-media",
            "name": "asset.webp",
            "size": "4",
            "md5Checksum": "md5",
            "appProperties": {
                "backupMd5": "md5",
                "backupSha256": "sha256",
            },
        },
        key,
    )
    manifest = backup.crear_manifest(
        "state",
        "2026-08-20T10:00:00Z",
        {"id": "db", "name": "db.dump", "size": "10", "md5Checksum": "db-md5"},
        {"bytes": 10, "md5": "db-md5", "sha256": "db-sha256"},
        [item],
        {"found": 1, "new": 1, "reused": 0, "errors": 0},
        "cloud-name",
    )

    assert manifest["restore"]["order"] == ["cloudinary", "postgresql"]
    for field in (
        "asset_id",
        "public_id",
        "secure_url",
        "resource_type",
        "type",
        "format",
        "bytes",
        "version",
        "folder",
        "asset_folder",
        "created_at",
        "checksum",
        "google_drive_filename",
    ):
        assert field in manifest["assets"][0]


def test_dry_run_does_not_dump_or_write(monkeypatch):
    monkeypatch.setattr(
        backup,
        "configurar_cloudinary",
        lambda: types.SimpleNamespace(cloud_name="test"),
    )
    monkeypatch.setattr(backup, "obtener_drive", lambda: object())
    monkeypatch.setattr(
        backup,
        "preparar_carpetas",
        lambda *_args, **_kwargs: {
            "root": "root",
            "database": "database",
            "manifests": "manifests",
            "media": "media",
        },
    )
    monkeypatch.setattr(
        backup,
        "respaldar_media",
        lambda *_args, **_kwargs: (
            [],
            {"found": 0, "new": 0, "reused": 0, "errors": 0},
        ),
    )
    monkeypatch.setattr(
        backup,
        "crear_dump",
        lambda *_args: (_ for _ in ()).throw(AssertionError("no debe ejecutarse")),
    )

    backup.ejecutar_backup(dry_run=True)


def test_pg_dump_receives_postgres_uri_only_through_environment(tmp_path, monkeypatch):
    postgres_uri = "postgresql://user:secret@database.internal:5432/catalogo"
    dump_path = tmp_path / "catalogo.dump"
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if command[0] == "pg_dump":
            dump_path.write_bytes(b"valid-dump")

    monkeypatch.setattr(backup, "POSTGRES_URI", postgres_uri)
    monkeypatch.setattr(backup.subprocess, "run", fake_run)

    backup.crear_dump(str(dump_path))

    dump_command, dump_options = calls[0]
    restore_command, restore_options = calls[1]
    assert postgres_uri not in dump_command
    assert dump_options["env"] is not backup.os.environ
    assert dump_options["env"]["PGDATABASE"] == postgres_uri
    assert restore_command == ["pg_restore", "--list", str(dump_path)]
    assert "env" not in restore_options
