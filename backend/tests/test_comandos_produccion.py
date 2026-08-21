from sqlalchemy import func, select

from app.extensiones import db
from app.modelos import Category, Role, User


ADMIN_ENV = {
    "CORREO_ADMINISTRADOR_INICIAL": "admin.inicial@gmail.com",
    "CONTRASENA_ADMINISTRADOR_INICIAL": "SeguraInicial2026!",
    "NOMBRES_ADMINISTRADOR_INICIAL": "Admin",
    "APELLIDO_PATERNO_ADMINISTRADOR_INICIAL": "Inicial",
    "APELLIDO_MATERNO_ADMINISTRADOR_INICIAL": "Sistema",
    "USUARIO_ADMINISTRADOR_INICIAL": "admin.inicial",
}


def test_seed_inicial_is_idempotent(app, monkeypatch):
    for key, value in ADMIN_ENV.items():
        monkeypatch.setenv(key, value)
    runner = app.test_cli_runner()
    assert runner.invoke(args=["seed-inicial"]).exit_code == 0
    assert runner.invoke(args=["seed-inicial"]).exit_code == 0
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User).where(User.role == Role.ADMIN)) == 1
        assert db.session.scalar(select(func.count()).select_from(Category)) == 5


def test_reset_requires_literal_confirmation_and_dry_run_does_not_write(app, monkeypatch):
    for key, value in ADMIN_ENV.items():
        monkeypatch.setenv(key, value)
    runner = app.test_cli_runner()
    assert runner.invoke(args=["seed-inicial"]).exit_code == 0
    dry = runner.invoke(args=["reset-produccion", "--dry-run"])
    assert dry.exit_code == 0 and "DRY-RUN" in dry.output
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 1
    denied = runner.invoke(args=["reset-produccion", "--confirm", "incorrecto"])
    assert denied.exit_code != 0
    done = runner.invoke(args=["reset-produccion", "--confirm", "RESET-PRODUCTION"])
    assert done.exit_code == 0
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(User)) == 0
        assert db.session.scalar(select(func.count()).select_from(Category)) == 0


def test_cloudinary_cleanup_is_paginated_scoped_and_confirmed(app):
    class FakeApi:
        deleted = []

        @classmethod
        def resources(cls, **options):
            if options["resource_type"] != "image" or options["type"] != "upload":
                return {"resources": []}
            if options.get("next_cursor"):
                return {"resources": [{"public_id": "otro-sistema/no-tocar"}]}
            return {"resources": [{"public_id": "catalogo-ministerio/productos/a"}], "next_cursor": "next"}

        @classmethod
        def delete_resources(cls, public_ids, **options):
            cls.deleted.extend(public_ids)

    from app.comandos_produccion import clean_cloudinary
    with app.app_context():
        assert clean_cloudinary(dry_run=True, confirmation=None, api=FakeApi) == 1
        assert FakeApi.deleted == []
        assert clean_cloudinary(dry_run=False, confirmation="DELETE-CLOUDINARY", api=FakeApi) == 1
        assert FakeApi.deleted == ["catalogo-ministerio/productos/a"]
