import os
import click
from flask.cli import with_appcontext
from sqlalchemy import select
from .extensions import db
from .models import User,Role,UserStatus,ExhibitorType,Category
from .utils import slugify,valid_gmail

def register_commands(app):
    @app.cli.command("seed-admin")
    @with_appcontext
    def seed_admin():
        email=os.getenv("INITIAL_ADMIN_EMAIL","").lower();password=os.getenv("INITIAL_ADMIN_PASSWORD","")
        if not valid_gmail(email):
            raise click.ClickException(
                "INITIAL_ADMIN_EMAIL debe ser una dirección válida terminada en @gmail.com"
            )
        password_rules = (
            len(password) >= 10,
            any(char.isupper() for char in password),
            any(char.islower() for char in password),
            any(char.isdigit() for char in password),
            any(not char.isalnum() for char in password),
        )
        if not all(password_rules):
            raise click.ClickException(
                "INITIAL_ADMIN_PASSWORD debe tener al menos 10 caracteres, "
                "una mayúscula, una minúscula, un número y un carácter especial"
            )
        if db.session.scalar(select(User).where(User.email==email)):click.echo("El administrador ya existe");return
        u=User(username=slugify(email.split('@')[0]),email=email,role=Role.SUPERADMIN,first_name=os.getenv("INITIAL_ADMIN_FIRST_NAME","Administrador"),last_name=os.getenv("INITIAL_ADMIN_LAST_NAME","Principal"),status=UserStatus.ACTIVE,must_change_password=True);u.set_password(password);db.session.add(u);db.session.commit();click.echo(f"SUPERADMIN creado: {u.username}")
    @app.cli.command("seed-catalogs")
    @with_appcontext
    def seed_catalogs():
        for name in ["Microempresa","Productor","Artesano","Emprendimiento","Asociación","Cooperativa","Otro"]:
            if not db.session.scalar(select(ExhibitorType).where(ExhibitorType.nombre==name)):db.session.add(ExhibitorType(nombre=name))
        for name in ["Alimentos","Artesanías","Textiles","Cosmética natural","Otros"]:
            if not db.session.scalar(select(Category).where(Category.nombre==name)):db.session.add(Category(nombre=name,slug=slugify(name)))
        db.session.commit();click.echo("Catálogos iniciales creados")
