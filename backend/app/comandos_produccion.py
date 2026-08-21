import os
import re

import click
from flask.cli import with_appcontext
from sqlalchemy import delete, func, inspect, select

from .extensiones import db
from .modelos import Category, ExhibitorType, ProductiveSector, Role, SectorStatus, User, UserStatus
from .servicios.archivos import CLOUDINARY_ROOT_FOLDER
from .utilidades import slugify, valid_gmail


EXHIBITOR_TYPES = (
    "Microempresa", "Productor", "Artesano", "Emprendimiento",
    "Asociación", "Cooperativa", "Otro",
)
CATEGORIES = ("Alimentos", "Artesanías", "Textiles", "Cosmética natural", "Otros")
PRODUCTIVE_SECTORS = (
    "Textiles y Confecciones", "Cuero y Calzados",
    "Alimentos y Bebidas Procesados", "Madera y Carpintería",
    "Orfebrería y Joyería", "Cosmética Natural y Cuidado Personal",
    "Artesanía Tradicional o Decorativa", "Otros",
)


def _table_counts():
    existing = set(inspect(db.engine).get_table_names())
    return {
        table.name: (db.session.scalar(select(func.count()).select_from(table)) if table.name in existing else 0)
        for table in db.metadata.sorted_tables
    }


def _echo_counts(counts, title):
    click.echo(title)
    for name in sorted(counts):
        click.echo(f"  {name}: {counts[name]}")


def reset_production(*, dry_run, confirmation):
    counts = _table_counts()
    _echo_counts(counts, "Registros encontrados:")
    if dry_run:
        click.echo("DRY-RUN: no se modificó PostgreSQL, Cloudinary ni ningún servicio externo.")
        return counts
    if confirmation != "RESET-PRODUCTION":
        raise click.ClickException("Confirme literalmente con --confirm RESET-PRODUCTION")

    try:
        # SQLAlchemy ordena las tablas por sus Foreign Keys; al invertir el orden,
        # cada tabla hija se vacía antes que su tabla padre.
        existing = set(inspect(db.engine).get_table_names())
        for table in reversed(db.metadata.sorted_tables):
            if table.name in existing:
                db.session.execute(delete(table))
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        raise click.ClickException("El reset falló; la transacción fue revertida") from exc

    after = _table_counts()
    _echo_counts(after, "Conteos después del reset:")
    click.echo("Reset de producción completado. Cloudinary no fue modificado.")
    return after


def _validate_admin_settings():
    email = os.getenv("CORREO_ADMINISTRADOR_INICIAL", "").lower().strip()
    password = os.getenv("CONTRASENA_ADMINISTRADOR_INICIAL", "")
    first_name = os.getenv("NOMBRES_ADMINISTRADOR_INICIAL", "Administrador").strip()
    paternal = os.getenv("APELLIDO_PATERNO_ADMINISTRADOR_INICIAL", "").strip() or "Principal"
    maternal = os.getenv("APELLIDO_MATERNO_ADMINISTRADOR_INICIAL", "").strip()
    username = os.getenv("USUARIO_ADMINISTRADOR_INICIAL", "").lower().strip()
    username = username or slugify(email.split("@")[0])
    if not valid_gmail(email):
        raise click.ClickException("CORREO_ADMINISTRADOR_INICIAL debe ser un correo válido")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,79}", username):
        raise click.ClickException("USUARIO_ADMINISTRADOR_INICIAL no tiene un formato válido")
    if not first_name or len(first_name) > 100 or not paternal or len(paternal) > 100 or len(maternal) > 100:
        raise click.ClickException("Los nombres y apellidos del ADMIN no son válidos")
    if not all((len(password) >= 10, any(c.isupper() for c in password),
                any(c.islower() for c in password), any(c.isdigit() for c in password),
                any(not c.isalnum() for c in password))):
        raise click.ClickException("CONTRASENA_ADMINISTRADOR_INICIAL no cumple la política")
    return email, password, first_name, paternal, maternal, username


def seed_initial():
    email, password, first_name, paternal, maternal, username = _validate_admin_settings()
    try:
        user = db.session.scalar(select(User).where((User.email == email) | (User.username == username)))
        if user and (user.email != email or user.username != username or user.role != Role.ADMIN):
            raise click.ClickException("El usuario o correo inicial ya pertenece a otra identidad")
        if not user:
            user = User(
                username=username, email=email, role=Role.ADMIN, first_name=first_name,
                last_name=paternal, apellido_paterno=paternal,
                apellido_materno=maternal or None, status=UserStatus.ACTIVE,
                must_change_password=True,
            )
            user.set_password(password)
            db.session.add(user)

        for name in EXHIBITOR_TYPES:
            item = db.session.scalar(select(ExhibitorType).where(ExhibitorType.nombre == name))
            if item:
                item.estado = True
            else:
                db.session.add(ExhibitorType(nombre=name, estado=True))
        for name in CATEGORIES:
            item = db.session.scalar(select(Category).where(Category.nombre == name))
            if item:
                item.estado, item.deleted_at = True, None
            else:
                db.session.add(Category(nombre=name, slug=slugify(name), estado=True))
        for name in PRODUCTIVE_SECTORS:
            item = db.session.scalar(select(ProductiveSector).where(ProductiveSector.nombre == name))
            if item:
                item.estado, item.deleted_at, item.es_otro = SectorStatus.ACTIVE, None, name == "Otros"
            else:
                db.session.add(ProductiveSector(nombre=name, estado=SectorStatus.ACTIVE, es_otro=name == "Otros"))
        db.session.commit()
    except click.ClickException:
        db.session.rollback()
        raise
    except Exception as exc:
        db.session.rollback()
        raise click.ClickException("No fue posible completar seed-inicial; se revirtió la transacción") from exc
    click.echo(
        f"Seed inicial listo: 1 ADMIN objetivo, {len(EXHIBITOR_TYPES)} tipos de expositor, "
        f"{len(CATEGORIES)} categorías y {len(PRODUCTIVE_SECTORS)} sectores."
    )


def _cloudinary_assets(api):
    seen = set()
    prefix = f"{CLOUDINARY_ROOT_FOLDER}/"
    for resource_type in ("image", "video", "raw"):
        for delivery_type in ("upload", "private", "authenticated"):
            cursor = None
            while True:
                options = dict(resource_type=resource_type, type=delivery_type, max_results=500)
                if cursor:
                    options["next_cursor"] = cursor
                response = api.resources(**options)
                for asset in response.get("resources", []):
                    public_id = str(asset.get("public_id") or "").lstrip("/")
                    folder = str(asset.get("asset_folder") or asset.get("folder") or "").strip("/")
                    if not (public_id.startswith(prefix) or folder == CLOUDINARY_ROOT_FOLDER or folder.startswith(prefix)):
                        continue
                    key = (resource_type, delivery_type, public_id)
                    if public_id and key not in seen:
                        seen.add(key)
                        yield key
                cursor = response.get("next_cursor")
                if not cursor:
                    break


def clean_cloudinary(*, dry_run, confirmation, api=None):
    if not dry_run and confirmation != "DELETE-CLOUDINARY":
        raise click.ClickException("Confirme literalmente con --confirm DELETE-CLOUDINARY")
    if api is None:
        try:
            import cloudinary
            import cloudinary.api
        except ModuleNotFoundError as exc:
            raise click.ClickException("Cloudinary no está instalado") from exc
        cloudinary.config(secure=True)
        cfg = cloudinary.config()
        if not all((cfg.cloud_name, cfg.api_key, cfg.api_secret)):
            raise click.ClickException("La configuración de Cloudinary está incompleta")
        api = cloudinary.api
    assets = list(_cloudinary_assets(api))
    for resource_type, delivery_type, public_id in assets:
        click.echo(f"  {resource_type}/{delivery_type}: {public_id}")
    click.echo(f"Assets dentro de {CLOUDINARY_ROOT_FOLDER}: {len(assets)}")
    if dry_run:
        click.echo("DRY-RUN: no se eliminó ningún asset.")
        return len(assets)
    for resource_type, delivery_type in {(a[0], a[1]) for a in assets}:
        ids = [a[2] for a in assets if a[:2] == (resource_type, delivery_type)]
        for start in range(0, len(ids), 100):
            api.delete_resources(ids[start:start + 100], resource_type=resource_type, type=delivery_type, invalidate=True)
    click.echo(f"Assets eliminados dentro de {CLOUDINARY_ROOT_FOLDER}: {len(assets)}")
    return len(assets)


def register_production_commands(app):
    @app.cli.command("reset-produccion")
    @click.option("--dry-run", is_flag=True, help="Solo cuenta y muestra el plan.")
    @click.option("--confirm", "confirmation")
    @with_appcontext
    def reset_produccion(dry_run, confirmation):
        reset_production(dry_run=dry_run, confirmation=confirmation)

    @app.cli.command("seed-inicial")
    @with_appcontext
    def seed_inicial():
        seed_initial()

    @app.cli.command("limpiar-cloudinary-produccion")
    @click.option("--dry-run", is_flag=True, help="Solo inventaría assets.")
    @click.option("--confirm", "confirmation")
    @with_appcontext
    def limpiar_cloudinary_produccion(dry_run, confirmation):
        clean_cloudinary(dry_run=dry_run, confirmation=confirmation)
