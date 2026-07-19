from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path
import os
from time import monotonic
import uuid

from flask import current_app, has_request_context, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import Audit, CacheState, ProductStatus, Role, User, UserStatus
from ..utils import slugify
from ..views import error

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
PUBLIC_CACHE = {}
PUBLIC_CACHE_KEY = "catalogo_publico"


def public_cache_version():
    state = db.session.scalar(
        select(CacheState).where(CacheState.key == PUBLIC_CACHE_KEY)
    )
    return state.version if state else 0


def invalidate_public_cache():
    state = db.session.scalar(
        select(CacheState)
        .where(CacheState.key == PUBLIC_CACHE_KEY)
        .with_for_update()
    )
    if state:
        state.version += 1
    else:
        db.session.add(CacheState(key=PUBLIC_CACHE_KEY, version=1))
    db.session.commit()
    PUBLIC_CACHE.clear()


def get_public_cache(key):
    cached = PUBLIC_CACHE.get(key)
    if not cached:
        return None
    version, expires_at, value = cached
    if version != public_cache_version() or expires_at <= monotonic():
        PUBLIC_CACHE.pop(key, None)
        return None
    return value


def set_public_cache(key, value):
    ttl = current_app.config["SEGUNDOS_MEMORIA_TEMPORAL_PUBLICA"]
    PUBLIC_CACHE[key] = (public_cache_version(), monotonic() + ttl, value)
    return value


def current_user():
    try:
        identity = get_jwt_identity()
    except RuntimeError:
        return None
    try:
        user_id = uuid.UUID(identity)
    except (ValueError, TypeError, AttributeError):
        return None
    return db.session.get(User, user_id)


def roles(*allowed):
    def decorator(function):
        @wraps(function)
        @jwt_required()
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user or user.status != UserStatus.ACTIVE:
                return error("Cuenta no disponible", 403)
            if user.must_change_password:
                return error("Debe cambiar su contraseña", 403)
            if user.role not in allowed:
                return error("No autorizado", 403)
            return function(*args, **kwargs)

        return wrapped

    return decorator


AUDIT_ACTION_DESCRIPTIONS = {
    "CREAR": "Creación",
    "EDITAR": "Edición",
    "ELIMINAR": "Eliminación",
    "CAMBIAR_ESTADO": "Cambio de estado",
    "SINCRONIZAR_ESTADO": "Sincronización automática del estado",
    "AGREGAR_IMAGEN": "Adición de imagen",
    "EDITAR_IMAGEN": "Edición de imagen",
    "ELIMINAR_IMAGEN": "Eliminación de imagen",
    "ASIGNAR": "Asignación",
    "CAMBIAR_CONTRASENA": "Cambio de contraseña",
    "RESTABLECER_CONTRASENA": "Restablecimiento de contraseña",
}


def audit_description(action, entity):
    action_text = AUDIT_ACTION_DESCRIPTIONS.get(
        action, (action or "Acción").replace("_", " ").capitalize()
    )
    return f"{action_text} de {entity.lower()}"


def audit(action, entity, entity_id=None, description=None, before=None, after=None):
    user = current_user() if has_request_context() else None
    db.session.add(
        Audit(
            user_id=user.id if user else None,
            accion=action,
            entidad=entity,
            entidad_id=entity_id,
            descripcion=(description or "").strip() or audit_description(action, entity),
            datos_anteriores=before,
            datos_nuevos=after,
            ip_address=request.remote_addr if has_request_context() else None,
            user_agent=(request.user_agent.string[:500] if has_request_context() else None),
        )
    )


def unique_username(first_name, last_name):
    base = slugify(f"{first_name}.{last_name}").replace("-", ".") or "usuario"
    candidate = base
    number = 1
    while db.session.scalar(select(User.id).where(User.username == candidate)):
        candidate = f"{base}{number:02d}"
        number += 1
    return candidate


def parse_money(value):
    if value in (None, ""):
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("El precio debe ser numérico") from exc
    if amount < 0:
        raise ValueError("El precio no puede ser negativo")
    return amount.quantize(Decimal("0.01"))


def product_from_payload(product, data, exhibitor_id=None):
    if exhibitor_id:
        product.exhibitor_id = exhibitor_id
    if "category_id" in data:
        try:
            value = data.get("category_id")
            product.category_id = value if isinstance(value, uuid.UUID) else uuid.UUID(value or "")
        except (ValueError, TypeError) as exc:
            raise ValueError("Categoría inválida") from exc
    if "nombre" in data:
        name = (data.get("nombre") or "").strip()
        if not name:
            raise ValueError("El nombre del producto es obligatorio")
        product.nombre = name
        product.slug = slugify(name)
    if "descripcion" in data:
        product.descripcion = data.get("descripcion") or ""
    if "precio" in data:
        product.precio = parse_money(data.get("precio"))
    for field in (
        "materiales_o_ingredientes",
        "lugar_origen",
        "presentacion",
        "informacion_adicional",
    ):
        if field in data:
            setattr(product, field, data.get(field))
    if "estado" in data:
        try:
            product.estado = ProductStatus(data.get("estado"))
        except ValueError as exc:
            raise ValueError("Estado de producto inválido") from exc
    if "destacado" in data:
        product.destacado = bool(data.get("destacado"))
    return product


def save_upload(file, folder):
    if not file or not file.filename:
        return None
    extension = file.filename.rsplit(".", 1)[-1].lower()
    if "." not in file.filename or extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Formato de imagen no permitido")
    try:
        image = Image.open(file.stream)
        image.verify()
        file.stream.seek(0)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("El archivo no es una imagen válida") from exc
    name = secure_filename(f"{uuid.uuid4().hex}.{extension}")
    target = Path(current_app.config["CARPETA_CARGAS"]) / folder
    target.mkdir(parents=True, exist_ok=True)
    file.save(target / name)
    return f"/uploads/{folder}/{name}"


def managed_upload_path(url, expected_folder=None):
    if not url or not url.startswith("/uploads/"):
        return None
    relative = url.removeprefix("/uploads/")
    if expected_folder and not relative.startswith(f"{expected_folder}/"):
        return None
    root = Path(current_app.config["CARPETA_CARGAS"]).resolve()
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


def require_managed_upload(url, folder):
    path = managed_upload_path(url, folder)
    if not path or not path.is_file():
        raise ValueError(f"La imagen debe subirse primero en la carpeta {folder}")
    return path


def delete_managed_upload(url, folder=None):
    path = managed_upload_path(url, folder)
    if path and path.is_file():
        path.unlink()
