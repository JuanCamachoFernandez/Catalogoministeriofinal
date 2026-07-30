from sqlalchemy import select

from ..extensiones import db
from ..modelos import ProductiveUnit, ProductiveUnitStatus, Role, User
from ..utilidades import slugify


def unique_username(first_name, last_name):
    base = slugify(f"{first_name}.{last_name}").replace("-", ".") or "usuario"
    candidate = base
    number = 1
    while db.session.scalar(select(User.id).where(User.username == candidate)):
        candidate = f"{base}{number:02d}"
        number += 1
    return candidate


def buscar_usuario_para_login(valor):
    usuario = db.session.scalar(select(User).where(User.username == valor))
    if usuario:
        return usuario
    usuario_correo = db.session.scalar(select(User).where(User.email == valor))
    if usuario_correo and usuario_correo.role == Role.PRODUCTIVE_UNIT_RESPONSIBLE:
        return usuario_correo
    return None


def obtener_unidad_activa_usuario(usuario_id):
    return db.session.scalar(
        select(ProductiveUnit).where(
            ProductiveUnit.user_id == usuario_id,
            ProductiveUnit.estado == ProductiveUnitStatus.ACTIVE,
            ProductiveUnit.deleted_at.is_(None),
        )
    )
