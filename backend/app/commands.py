import os
from pathlib import Path

import click
from flask.cli import with_appcontext
from sqlalchemy import select

from .extensions import db
from .models import Category, ExhibitorType, Fair, FairImage, Role, User, UserStatus
from .utils import slugify, valid_gmail


def register_commands(app):
    @app.cli.command("sync-fairs")
    @with_appcontext
    def sync_fairs():
        from .controllers.common import managed_upload_path
        from .controllers.fair_controller import sync_fair_lifecycle

        changed = sync_fair_lifecycle()
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
        folder = Path(app.config["UPLOAD_FOLDER"]) / "ferias"
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

    @app.cli.command("seed-admin")
    @with_appcontext
    def seed_admin():
        email = os.getenv("INITIAL_ADMIN_EMAIL", "").lower()
        password = os.getenv("INITIAL_ADMIN_PASSWORD", "")
        if not valid_gmail(email):
            raise click.ClickException(
                "INITIAL_ADMIN_EMAIL debe ser una dirección válida terminada en @gmail.com"
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
                "INITIAL_ADMIN_PASSWORD debe tener al menos 10 caracteres, una mayúscula, "
                "una minúscula, un número y un carácter especial"
            )
        if db.session.scalar(select(User).where(User.email == email)):
            click.echo("El administrador ya existe")
            return
        user = User(
            username=slugify(email.split("@")[0]),
            email=email,
            role=Role.SUPERADMIN,
            first_name=os.getenv("INITIAL_ADMIN_FIRST_NAME", "Administrador"),
            last_name=os.getenv("INITIAL_ADMIN_LAST_NAME", "Principal"),
            status=UserStatus.ACTIVE,
            must_change_password=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"SUPERADMIN creado: {user.username}")

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
