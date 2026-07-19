from datetime import datetime, timezone
import uuid
from urllib.parse import urlparse
import unicodedata

from flask import Blueprint, current_app, request
from sqlalchemy import func, select

from ..extensions import db
from ..models import (
    AdminProfile,
    DocumentType,
    Exhibitor,
    ExhibitorType,
    ExhibitorTypeLink,
    Role,
    User,
    UserStatus,
)
from ..utils import document_initial_password, normalize_whatsapp, valid_gmail
from ..views import error, exhibitor_json, paginate, validate_json, validated_json
from ..views.exhibitor_view import (
    ExhibitorCreateSchema,
    ExhibitorStatusSchema,
    ExhibitorUpdateSchema,
)
from .common import (
    audit,
    current_user,
    delete_managed_upload,
    invalidate_public_cache,
    require_managed_upload,
    roles,
    unique_username,
)


def validate_logo_reference(value):
    if not value:
        return
    parsed = urlparse(value)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return
    require_managed_upload(value, "logos")

exhibitor_bp = Blueprint("exhibitors", __name__)


def update_exhibitor_fields(exhibitor, data):
    if "apellido_paterno_responsable" not in data and data.get("apellido_responsable"):
        data["apellido_paterno_responsable"] = data["apellido_responsable"]
    if "correo" in data:
        email = (data.get("correo") or "").lower().strip()
        if not valid_gmail(email):
            raise ValueError("El correo debe ser una dirección @gmail.com válida")
        duplicate = db.session.scalar(
            select(Exhibitor.id).where(
                Exhibitor.correo == email, Exhibitor.id != exhibitor.id
            )
        )
        if duplicate:
            raise ValueError("El Gmail ya está registrado")
        exhibitor.correo = email
        exhibitor.user.email = email
    if "telefono_whatsapp" in data:
        exhibitor.telefono_whatsapp = normalize_whatsapp(data.get("telefono_whatsapp"))
        exhibitor.user.phone = exhibitor.telefono_whatsapp
    if "tipo_documento" in data:
        exhibitor.tipo_documento = DocumentType(data.get("tipo_documento"))
    old_logo = None
    if "logo" in data and data.get("logo") != exhibitor.logo:
        if data.get("logo"):
            validate_logo_reference(data.get("logo"))
        old_logo = exhibitor.logo
    for field in (
        "nombre_comercial",
        "numero_documento",
        "nombre_responsable",
        "apellido_paterno_responsable",
        "apellido_materno_responsable",
        "departamento",
        "municipio",
        "direccion",
        "descripcion",
        "descripcion_productos",
        "nombre_tipo_expositor",
        "logo",
    ):
        if field in data:
            setattr(exhibitor, field, data.get(field))
    if data.get("apellido_paterno_responsable"):
        exhibitor.apellido_responsable = data["apellido_paterno_responsable"]
        exhibitor.user.last_name = data["apellido_paterno_responsable"]
    if data.get("nombre_responsable"):
        exhibitor.user.first_name = data["nombre_responsable"]
    return old_logo


def normalized_type_name(value):
    return "".join(
        character
        for character in unicodedata.normalize("NFKD", value or "")
        if not unicodedata.combining(character)
    ).casefold()


def type_requires_name(type_item):
    return normalized_type_name(type_item.nombre) in {
        "asociacion",
        "cooperativa",
        "emprendimiento",
        "microempresa",
    }


def selected_exhibitor_type(type_ids):
    if len(type_ids or []) != 1:
        raise ValueError("Seleccione un solo tipo de expositor")
    value = type_ids[0]
    type_id = value if isinstance(value, uuid.UUID) else uuid.UUID(value)
    type_item = db.session.get(ExhibitorType, type_id)
    if not type_item or not type_item.estado:
        raise ValueError("Tipo de expositor inexistente")
    return type_item


def validate_type_name(type_item, value):
    name = (value or "").strip()
    if type_requires_name(type_item) and not name:
        raise ValueError(f"Ingrese el nombre de la {type_item.nombre.lower()}")
    return name if type_requires_name(type_item) else None


@exhibitor_bp.get("/exhibitor-types")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def exhibitor_types():
    items = db.session.scalars(
        select(ExhibitorType)
        .where(ExhibitorType.estado.is_(True))
        .order_by(ExhibitorType.nombre)
    ).all()
    return {"items": [{"id": str(item.id), "nombre": item.nombre} for item in items]}


@exhibitor_bp.get("/exhibitors")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def list_exhibitors():
    term = request.args.get("q", "").strip()
    state = None
    if request.args.get("estado"):
        try:
            state = UserStatus(request.args["estado"])
        except ValueError:
            return error("Estado inválido")
    query = Exhibitor.admin_query(term, request.args.get("departamento"), state)
    if request.args.get("municipio"):
        query = query.where(Exhibitor.municipio == request.args["municipio"])
    if request.args.get("tipo_documento") in {item.value for item in DocumentType}:
        query = query.where(Exhibitor.tipo_documento == DocumentType(request.args["tipo_documento"]))
    if request.args.get("date_from"):
        query = query.where(func.date(Exhibitor.created_at) >= request.args["date_from"])
    if request.args.get("date_to"):
        query = query.where(func.date(Exhibitor.created_at) <= request.args["date_to"])
    return paginate(query.order_by(Exhibitor.created_at.desc()), exhibitor_json)


@exhibitor_bp.get("/exhibitors/<uuid:exhibitor_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def get_exhibitor(exhibitor_id):
    exhibitor = db.session.get(Exhibitor, exhibitor_id)
    if not exhibitor or exhibitor.deleted_at:
        return error("Expositor no encontrado", 404)
    return exhibitor_json(exhibitor)


@exhibitor_bp.post("/exhibitors")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(ExhibitorCreateSchema())
def create_exhibitor():
    data = validated_json()
    email = (data.get("correo") or "").lower().strip()
    type_ids = data.get("type_ids") or []
    apellido_paterno = (
        data.get("apellido_paterno_responsable") or data.get("apellido_responsable")
    )
    apellido_materno = data.get("apellido_materno_responsable")
    if not valid_gmail(email):
        return error("El correo debe ser una dirección @gmail.com válida")
    if len(type_ids) != 1:
        return error("Seleccione un solo tipo de expositor")
    if db.session.scalar(select(User.id).where(User.email == email)):
        return error("El Gmail ya está registrado", 409)
    if db.session.scalar(
        select(Exhibitor.id).where(
            Exhibitor.numero_documento == data.get("numero_documento")
        )
    ) or db.session.scalar(
        select(AdminProfile.id).where(
            AdminProfile.numero_documento == data.get("numero_documento")
        )
    ):
        return error("El documento ya está registrado", 409)
    try:
        phone = normalize_whatsapp(data.get("telefono_whatsapp"))
        document_type = DocumentType(data.get("tipo_documento", "CI"))
        if data.get("logo"):
            validate_logo_reference(data.get("logo"))
        selected_type = selected_exhibitor_type(type_ids)
        type_specific_name = validate_type_name(
            selected_type, data.get("nombre_tipo_expositor")
        )
    except (ValueError, TypeError) as exc:
        return error(str(exc) or "Datos inválidos")
    required = [
        data.get(field)
        for field in (
            "nombre_comercial",
            "numero_documento",
            "nombre_responsable",
            "departamento",
            "municipio",
        )
    ]
    if not all(required) or not apellido_paterno:
        return error("Complete todos los campos obligatorios")
    password = document_initial_password(
        data["numero_documento"],
        data["nombre_responsable"],
        apellido_paterno,
    )
    user = User(
        username=unique_username(data["nombre_responsable"], apellido_paterno),
        email=email,
        role=Role.EXPOSITOR,
        first_name=data["nombre_responsable"],
        last_name=apellido_paterno,
        phone=phone,
        status=UserStatus.ACTIVE,
        must_change_password=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    exhibitor = Exhibitor(
        user_id=user.id,
        nombre_comercial=data["nombre_comercial"],
        tipo_documento=document_type,
        numero_documento=data["numero_documento"],
        nombre_responsable=data["nombre_responsable"],
        apellido_responsable=apellido_paterno,
        apellido_paterno_responsable=apellido_paterno,
        apellido_materno_responsable=apellido_materno,
        telefono_whatsapp=phone,
        correo=email,
        departamento=data["departamento"],
        municipio=data["municipio"],
        direccion=data.get("direccion"),
        descripcion=data.get("descripcion"),
        descripcion_productos=data.get("descripcion_productos"),
        nombre_tipo_expositor=type_specific_name,
        logo=data.get("logo"),
        estado=UserStatus.ACTIVE,
    )
    db.session.add(exhibitor)
    db.session.flush()
    db.session.add(
        ExhibitorTypeLink(exhibitor_id=exhibitor.id, type_id=selected_type.id)
    )
    audit(
        "CREAR", "Expositor", exhibitor.id,
        f"Expositor y cuenta creados: {exhibitor.nombre_comercial or exhibitor.nombre_responsable}",
    )
    db.session.commit()
    response = {
        "message": "Expositor creado",
        "data": exhibitor_json(exhibitor),
        "username": user.username,
        "temporary_password": password,
    }
    return response, 201


@exhibitor_bp.patch("/exhibitors/<uuid:exhibitor_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(ExhibitorUpdateSchema())
def update_exhibitor(exhibitor_id):
    exhibitor = db.session.get(Exhibitor, exhibitor_id)
    if not exhibitor or exhibitor.deleted_at:
        return error("Expositor no encontrado", 404)
    data = validated_json()
    try:
        if "type_ids" in data:
            selected_type = selected_exhibitor_type(data["type_ids"])
        else:
            selected_type = db.session.scalar(
                select(ExhibitorType)
                .join(ExhibitorTypeLink, ExhibitorTypeLink.type_id == ExhibitorType.id)
                .where(ExhibitorTypeLink.exhibitor_id == exhibitor.id)
            )
        if selected_type:
            data["nombre_tipo_expositor"] = validate_type_name(
                selected_type,
                data.get("nombre_tipo_expositor", exhibitor.nombre_tipo_expositor),
            )
        old_logo = update_exhibitor_fields(exhibitor, data)
        if "type_ids" in data:
            db.session.execute(
                db.delete(ExhibitorTypeLink).where(
                    ExhibitorTypeLink.exhibitor_id == exhibitor.id
                )
            )
            db.session.add(
                ExhibitorTypeLink(
                    exhibitor_id=exhibitor.id, type_id=selected_type.id
                )
            )
    except ValueError as exc:
        return error(str(exc))
    audit(
        "EDITAR", "Expositor", exhibitor.id,
        f"Expositor actualizado: {exhibitor.nombre_comercial or exhibitor.nombre_responsable}",
    )
    db.session.commit()
    if old_logo:
        delete_managed_upload(old_logo, "logos")
    invalidate_public_cache()
    return exhibitor_json(exhibitor)


@exhibitor_bp.patch("/exhibitors/<uuid:exhibitor_id>/status")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(ExhibitorStatusSchema())
def exhibitor_status(exhibitor_id):
    exhibitor = db.session.get(Exhibitor, exhibitor_id)
    if not exhibitor or exhibitor.deleted_at:
        return error("Expositor no encontrado", 404)
    try:
        status = UserStatus(validated_json()["status"])
    except ValueError:
        return error("Estado inválido")
    exhibitor.estado = status
    exhibitor.user.status = status
    audit(
        "CAMBIAR_ESTADO",
        "Expositor",
        exhibitor.id,
        f"Estado de {exhibitor.nombre_comercial or exhibitor.nombre_responsable} cambiado a {status.value}",
    )
    db.session.commit()
    invalidate_public_cache()
    return exhibitor_json(exhibitor)


@exhibitor_bp.delete("/exhibitors/<uuid:exhibitor_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def delete_exhibitor(exhibitor_id):
    exhibitor = db.session.get(Exhibitor, exhibitor_id)
    if not exhibitor or exhibitor.deleted_at:
        return error("Expositor no encontrado", 404)
    exhibitor.deleted_at = datetime.now(timezone.utc)
    exhibitor.estado = UserStatus.INACTIVE
    exhibitor.user.deleted_at = exhibitor.deleted_at
    exhibitor.user.status = UserStatus.INACTIVE
    audit(
        "ELIMINAR", "Expositor", exhibitor.id,
        f"Expositor eliminado: {exhibitor.nombre_comercial or exhibitor.nombre_responsable}",
    )
    db.session.commit()
    invalidate_public_cache()
    return "", 204


@exhibitor_bp.get("/exhibitor/profile")
@roles(Role.EXPOSITOR)
def own_profile():
    exhibitor = current_user().exhibitor
    if not exhibitor or exhibitor.deleted_at:
        return error("Perfil no encontrado", 404)
    return exhibitor_json(exhibitor)


@exhibitor_bp.patch("/exhibitor/profile")
@roles(Role.EXPOSITOR)
@validate_json(ExhibitorUpdateSchema())
def update_own_profile():
    exhibitor = current_user().exhibitor
    data = validated_json()
    allowed = {
        key: value
        for key, value in data.items()
        if key
        in {
            "nombre_comercial",
            "telefono_whatsapp",
            "departamento",
            "municipio",
            "direccion",
            "descripcion",
            "descripcion_productos",
            "logo",
        }
    }
    try:
        old_logo = update_exhibitor_fields(exhibitor, allowed)
    except ValueError as exc:
        return error(str(exc))
    audit("EDITAR", "Expositor", exhibitor.id, "Perfil actualizado por expositor")
    db.session.commit()
    if old_logo:
        delete_managed_upload(old_logo, "logos")
    invalidate_public_cache()
    return exhibitor_json(exhibitor)
