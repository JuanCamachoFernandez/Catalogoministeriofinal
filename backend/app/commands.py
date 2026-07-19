from datetime import datetime, timezone
import os
import re
from pathlib import Path

import click
from flask.cli import with_appcontext
from sqlalchemy import delete, select, text
from sqlalchemy.engine import make_url

from .extensions import db
from .models import (
    Category,
    ExhibitorType,
    Fair,
    FairImage,
    RevokedToken,
    Role,
    User,
    UserStatus,
)
from .utils import slugify, valid_gmail


def register_commands(app):
    @app.cli.command("sync-fairs")
    @with_appcontext
    def sync_fairs():
        from .controllers.common import managed_upload_path
        from .controllers.fair_controller import sync_fair_lifecycle

        changed = sync_fair_lifecycle()
        expired_tokens = db.session.execute(
            delete(RevokedToken).where(
                RevokedToken.expires_at <= datetime.now(timezone.utc)
            )
        ).rowcount
        db.session.commit()
        urls = [
            *db.session.scalars(
                select(Fair.imagen_portada).where(Fair.imagen_portada.is_not(None))
            ).all(),
            *db.session.scalars(select(FairImage.url)).all(),
        ]
        referenced = {
            path.resolve()
            for url in urls
            if (path := managed_upload_path(url, "ferias"))
        }
        folder = Path(app.config["CARPETA_CARGAS"]) / "ferias"
        removed = 0
        if folder.exists():
            for path in folder.iterdir():
                if path.is_file() and path.resolve() not in referenced:
                    path.unlink()
                    removed += 1
        click.echo(
            f"Ferias: {'actualizadas' if changed else 'sin cambios'}; "
            f"archivos huérfanos eliminados: {removed}"
        )

        click.echo(f"Tokens revocados expirados eliminados: {expired_tokens}")

    def require_postgresql_test_database():
        url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
        database_name = url.database or ""
        if url.get_backend_name() != "postgresql" or not database_name.endswith("_test"):
            raise click.ClickException(
                "Este comando solo acepta PostgreSQL y una base cuyo nombre termine en _test"
            )

    @app.cli.command("reset-test-db")
    @click.option("--yes", is_flag=True)
    @with_appcontext
    def reset_test_db(yes):
        """Reconstruye una base PostgreSQL de prueba desde las migraciones."""
        require_postgresql_test_database()
        if not yes:
            raise click.ClickException("Confirme la operaciÃ³n con --yes")
        db.session.execute(text("DROP SCHEMA public CASCADE"))
        db.session.execute(text("CREATE SCHEMA public"))
        db.session.commit()
        from flask_migrate import upgrade

        upgrade()
        click.echo("Base de prueba reconstruida desde migraciones")

    @app.cli.command("seed-test-data")
    @with_appcontext
    def seed_test_data():
        """Carga catÃ¡logos y un SUPERADMIN predecible para pruebas."""
        require_postgresql_test_database()
        email = os.getenv("CORREO_ADMINISTRADOR_PRUEBAS", "catalogo.test@gmail.com").lower()
        password = os.getenv("CONTRASENA_ADMINISTRADOR_PRUEBAS", "Catalogo.Test123!")
        if not db.session.scalar(select(User.id).where(User.email == email)):
            user = User(
                username="catalogo.test",
                email=email,
                role=Role.SUPERADMIN,
                first_name="Administrador",
                last_name="Pruebas",
                status=UserStatus.ACTIVE,
                must_change_password=False,
            )
            user.set_password(password)
            db.session.add(user)
        for name in ["Microempresa", "Productor", "Artesano", "Emprendimiento"]:
            if not db.session.scalar(
                select(ExhibitorType.id).where(ExhibitorType.nombre == name)
            ):
                db.session.add(ExhibitorType(nombre=name))
        for name in ["Alimentos", "ArtesanÃ­as", "Textiles", "Otros"]:
            if not db.session.scalar(select(Category.id).where(Category.nombre == name)):
                db.session.add(Category(nombre=name, slug=slugify(name)))
        db.session.commit()
        click.echo(f"Datos de prueba creados; administrador: {email}")

    @app.cli.command("seed-admin")
    @with_appcontext
    def seed_admin():
        email = os.getenv("CORREO_ADMINISTRADOR_INICIAL", "").lower().strip()
        password = os.getenv("CONTRASENA_ADMINISTRADOR_INICIAL", "")
        first_name = os.getenv("NOMBRES_ADMINISTRADOR_INICIAL", "Administrador").strip()
        paternal_last_name = (
            os.getenv("APELLIDO_PATERNO_ADMINISTRADOR_INICIAL", "").strip()
            or "Principal"
        )
        maternal_last_name = os.getenv("APELLIDO_MATERNO_ADMINISTRADOR_INICIAL", "").strip()
        username = os.getenv("USUARIO_ADMINISTRADOR_INICIAL", "").lower().strip()
        if not username:
            username = slugify(email.split("@")[0])
        if not valid_gmail(email):
            raise click.ClickException(
                "CORREO_ADMINISTRADOR_INICIAL debe ser una dirección válida terminada en @gmail.com"
            )
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,79}", username):
            raise click.ClickException(
                "USUARIO_ADMINISTRADOR_INICIAL debe tener entre 3 y 80 caracteres y usar "
                "solo letras minúsculas, números, punto, guion o guion bajo"
            )
        if not first_name or len(first_name) > 100:
            raise click.ClickException(
                "NOMBRES_ADMINISTRADOR_INICIAL es obligatorio y admite hasta 100 caracteres"
            )
        if not paternal_last_name or len(paternal_last_name) > 100:
            raise click.ClickException(
                "APELLIDO_PATERNO_ADMINISTRADOR_INICIAL es obligatorio y admite hasta 100 caracteres"
            )
        if len(maternal_last_name) > 100:
            raise click.ClickException(
                "APELLIDO_MATERNO_ADMINISTRADOR_INICIAL admite hasta 100 caracteres"
            )
        rules = (
            len(password) >= 10,
            any(char.isupper() for char in password),
            any(char.islower() for char in password),
            any(char.isdigit() for char in password),
            any(not char.isalnum() for char in password),
        )
        if not all(rules):
            raise click.ClickException(
                "CONTRASENA_ADMINISTRADOR_INICIAL debe tener al menos 10 caracteres, una mayúscula, "
                "una minúscula, un número y un carácter especial"
            )
        existing = db.session.scalar(
            select(User).where((User.email == email) | (User.username == username))
        )
        if existing:
            if existing.email == email and existing.username == username:
                click.echo("El administrador inicial ya existe")
                return
            raise click.ClickException(
                "El usuario o Gmail del administrador inicial ya está registrado"
            )
        user = User(
            username=username,
            email=email,
            role=Role.SUPERADMIN,
            first_name=first_name,
            last_name=paternal_last_name,
            apellido_paterno=paternal_last_name,
            apellido_materno=maternal_last_name or None,
            status=UserStatus.ACTIVE,
            must_change_password=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"SUPERADMIN creado: {user.username} ({user.first_name} {user.last_name})")

    @app.cli.command("seed-catalogs")
    @with_appcontext
    def seed_catalogs():
        for name in [
            "Microempresa",
            "Productor",
            "Artesano",
            "Emprendimiento",
            "Asociación",
            "Cooperativa",
            "Otro",
        ]:
            if not db.session.scalar(
                select(ExhibitorType).where(ExhibitorType.nombre == name)
            ):
                db.session.add(ExhibitorType(nombre=name))
        for name in ["Alimentos", "Artesanías", "Textiles", "Cosmética natural", "Otros"]:
            if not db.session.scalar(select(Category).where(Category.nombre == name)):
                db.session.add(Category(nombre=name, slug=slugify(name)))
        db.session.commit()
        click.echo("Catálogos iniciales creados")
