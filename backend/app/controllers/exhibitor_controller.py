from datetime import datetime, timezone
import uuid

from flask import Blueprint, current_app, request
from sqlalchemy import select

from ..email_service import BrevoEmailService, EmailDeliveryError
from ..extensions import db
from ..models import (
    DocumentType,
    Exhibitor,
    ExhibitorType,
    ExhibitorTypeLink,
    Role,
    User,
    UserStatus,
)
from ..utils import normalize_whatsapp, temporary_password, valid_gmail
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

exhibitor_bp = Blueprint("exhibitors", __name__)


def update_exhibitor_fields(exhibitor, data):
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
            require_managed_upload(data.get("logo"), "logos")
        old_logo = exhibitor.logo
    for field in (
        "nombre_comercial",
        "numero_documento",
        "nombre_responsable",
        "apellido_responsable",
        "departamento",
        "municipio",
        "direccion",
        "descripcion",
        "descripcion_productos",
        "logo",
    ):
        if field in data:
            setattr(exhibitor, field, data.get(field))
    return old_logo


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
    if not valid_gmail(email):
        return error("El correo debe ser una dirección @gmail.com válida")
    if not type_ids:
        return error("Seleccione al menos un tipo de expositor")
    if db.session.scalar(select(User.id).where(User.email == email)):
        return error("El Gmail ya está registrado", 409)
    if db.session.scalar(
        select(Exhibitor.id).where(
            Exhibitor.numero_documento == data.get("numero_documento")
        )
    ):
        return error("El documento ya está registrado", 409)
    try:
        phone = normalize_whatsapp(data.get("telefono_whatsapp"))
        document_type = DocumentType(data.get("tipo_documento", "CI"))
        if data.get("logo"):
            require_managed_upload(data.get("logo"), "logos")
        parsed_types = [
            value if isinstance(value, uuid.UUID) else uuid.UUID(value)
            for value in type_ids
        ]
    except (ValueError, TypeError) as exc:
        return error(str(exc) or "Datos inválidos")
    required = [
        data.get(field)
        for field in (
            "nombre_comercial",
            "numero_documento",
            "nombre_responsable",
            "apellido_responsable",
            "departamento",
            "municipio",
        )
    ]
    if not all(required):
        return error("Complete todos los campos obligatorios")
    for type_id in parsed_types:
        if not db.session.get(ExhibitorType, type_id):
            return error("Tipo de expositor inexistente")
    password = temporary_password()
    user = User(
        username=unique_username(data["nombre_responsable"], data["apellido_responsable"]),
        email=email,
        role=Role.EXPOSITOR,
        first_name=data["nombre_responsable"],
        last_name=data["apellido_responsable"],
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
        apellido_responsable=data["apellido_responsable"],
        telefono_whatsapp=phone,
        correo=email,
        departamento=data["departamento"],
        municipio=data["municipio"],
        direccion=data.get("direccion"),
        descripcion=data.get("descripcion"),
        descripcion_productos=data.get("descripcion_productos"),
        logo=data.get("logo"),
        estado=UserStatus.ACTIVE,
    )
    db.session.add(exhibitor)
    db.session.flush()
    for type_id in parsed_types:
        db.session.add(ExhibitorTypeLink(exhibitor_id=exhibitor.id, type_id=type_id))
    audit("CREAR", "Expositor", exhibitor.id, "Expositor y cuenta creados")
    db.session.commit()
    service = BrevoEmailService()
    try:
        delivery = service.send_credentials(
            email,
            f"{user.first_name} {user.last_name}",
            user.username,
            password,
        )
    except EmailDeliveryError:
        current_app.logger.exception("No se pudieron enviar credenciales")
        delivery = {"sent": False}
    response = {
        "message": "Expositor creado",
        "data": exhibitor_json(exhibitor),
        "username": user.username,
        "email_sent": delivery.get("sent", False),
    }
    if not service.enabled:
        response["temporary_password"] = password
    return response, 201


@exhibitor_bp.patch("/exhibitors/<uuid:exhibitor_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(ExhibitorUpdateSchema())
def update_exhibitor(exhibitor_id):
    exhibitor = db.session.get(Exhibitor, exhibitor_id)
    if not exhibitor or exhibitor.deleted_at:
        return error("Expositor no encontrado", 404)
    try:
        old_logo = update_exhibitor_fields(exhibitor, validated_json())
    except ValueError as exc:
        return error(str(exc))
    audit("EDITAR", "Expositor", exhibitor.id, "Expositor actualizado")
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
    audit("CAMBIAR_ESTADO", "Expositor", exhibitor.id)
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
    audit("ELIMINAR", "Expositor", exhibitor.id, "Eliminación lógica")
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
