from datetime import datetime, timezone

from flask import Blueprint, current_app, request
from sqlalchemy import func, select

from ..email_service import BrevoEmailService, EmailDeliveryError
from ..extensions import db
from ..models import (
    AdminProfile,
    AssignmentStatus,
    Audit,
    Exhibitor,
    Fair,
    FairExhibitor,
    FeriaStatus,
    Product,
    ProductStatus,
    Role,
    User,
    UserStatus,
)
from ..utils import temporary_password, valid_gmail
from ..views import admin_user_json, error, paginate, validate_json, validated_json
from ..views.admin_view import AdminCreateSchema, AdminUpdateSchema, UserStatusSchema
from .auth_controller import strong_password
from .common import audit, current_user, roles, unique_username

admin_bp = Blueprint("admin", __name__)


def deliver_credentials(user, password):
    service = BrevoEmailService()
    try:
        result = service.send_credentials(
            user.email,
            f"{user.first_name} {user.last_name}",
            user.username,
            password,
        )
    except EmailDeliveryError:
        current_app.logger.exception("No se pudieron enviar las credenciales")
        result = {"sent": False, "reason": "delivery_error"}
    return result


@admin_bp.get("/admin/dashboard")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def admin_dashboard():
    from .fair_controller import sync_fair_lifecycle

    sync_fair_lifecycle()
    count = lambda model, *conditions: db.session.scalar(
        select(func.count()).select_from(model).where(*conditions)
    ) or 0
    active = db.session.scalar(Fair.active_query())
    audits = db.session.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(8)).all()
    return {
        "stats": {
            "ferias": count(Fair, Fair.deleted_at.is_(None)),
            "feria_activa": active.nombre if active else None,
            "ferias_publicadas": count(
                Fair, Fair.estado == FeriaStatus.PUBLISHED, Fair.deleted_at.is_(None)
            ),
            "expositores": count(Exhibitor, Exhibitor.deleted_at.is_(None)),
            "expositores_activos": count(
                Exhibitor,
                Exhibitor.estado == UserStatus.ACTIVE,
                Exhibitor.deleted_at.is_(None),
            ),
            "productos": count(Product, Product.deleted_at.is_(None)),
            "productos_disponibles": count(
                Product,
                Product.estado == ProductStatus.AVAILABLE,
                Product.deleted_at.is_(None),
            ),
            "productos_sin_stock": count(
                Product,
                Product.estado == ProductStatus.OUT_OF_STOCK,
                Product.deleted_at.is_(None),
            ),
            "asignaciones_pendientes": count(
                FairExhibitor, FairExhibitor.estado == AssignmentStatus.PENDING
            ),
        },
        "recent_audits": [
            {
                "id": str(item.id),
                "accion": item.accion,
                "entidad": item.entidad,
                "descripcion": item.descripcion,
                "created_at": item.created_at.isoformat(),
            }
            for item in audits
        ],
    }


@admin_bp.get("/admin/users")
@roles(Role.SUPERADMIN)
def list_admin_users():
    term = request.args.get("q", "").strip()
    query = User.admin_query(term)
    return paginate(query.order_by(User.created_at.desc()), admin_user_json)


@admin_bp.get("/admin/users/<uuid:user_id>")
@roles(Role.SUPERADMIN)
def get_admin_user(user_id):
    user = db.session.get(User, user_id)
    if not user or user.deleted_at or user.role == Role.EXPOSITOR:
        return error("Administrador no encontrado", 404)
    return admin_user_json(user)


@admin_bp.post("/admin/users")
@roles(Role.SUPERADMIN)
@validate_json(AdminCreateSchema())
def create_admin_user():
    data = validated_json()
    email = (data.get("email") or "").lower().strip()
    try:
        role = Role(data.get("role", "ADMIN_VICEMINISTERIO"))
    except ValueError:
        return error("Rol administrativo inválido")
    if role not in (Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO):
        return error("Rol administrativo inválido")
    if not valid_gmail(email):
        return error("El correo debe ser una dirección @gmail.com válida")
    if db.session.scalar(select(User.id).where(User.email == email)):
        return error("El Gmail ya está registrado", 409)
    if not data.get("first_name") or not data.get("last_name"):
        return error("Nombres y apellidos son obligatorios")
    password = temporary_password()
    user = User(
        username=unique_username(data["first_name"], data["last_name"]),
        email=email,
        role=role,
        first_name=data["first_name"].strip(),
        last_name=data["last_name"].strip(),
        phone=data.get("phone"),
        status=UserStatus.ACTIVE,
        must_change_password=True,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.add(
        AdminProfile(
            user_id=user.id,
            cargo=data.get("cargo"),
            unidad=data.get("unidad"),
            observaciones=data.get("observaciones"),
        )
    )
    audit("CREAR", "Usuario", user.id, "Administrador creado")
    db.session.commit()
    delivery = deliver_credentials(user, password)
    response = {
        "message": "Administrador creado",
        "data": admin_user_json(user),
        "email_sent": delivery.get("sent", False),
    }
    if not BrevoEmailService().enabled:
        response["temporary_password"] = password
    return response, 201


@admin_bp.patch("/admin/users/<uuid:user_id>")
@roles(Role.SUPERADMIN)
@validate_json(AdminUpdateSchema())
def update_admin_user(user_id):
    user = db.session.get(User, user_id)
    data = validated_json()
    if not user or user.deleted_at or user.role == Role.EXPOSITOR:
        return error("Administrador no encontrado", 404)
    if "email" in data:
        email = (data.get("email") or "").lower().strip()
        if not valid_gmail(email):
            return error("El correo debe ser una dirección @gmail.com válida")
        duplicate = db.session.scalar(
            select(User.id).where(User.email == email, User.id != user.id)
        )
        if duplicate:
            return error("El Gmail ya está registrado", 409)
        user.email = email
    for field in ("first_name", "last_name", "phone"):
        if field in data:
            setattr(user, field, data.get(field))
    if user.admin_profile:
        for field in ("cargo", "unidad", "observaciones"):
            if field in data:
                setattr(user.admin_profile, field, data.get(field))
    audit("EDITAR", "Usuario", user.id, "Administrador actualizado")
    db.session.commit()
    return admin_user_json(user)


@admin_bp.patch("/admin/users/<uuid:user_id>/status")
@roles(Role.SUPERADMIN)
@validate_json(UserStatusSchema())
def change_admin_status(user_id):
    target = db.session.get(User, user_id)
    actor = current_user()
    if not target or target.role == Role.EXPOSITOR:
        return error("Administrador no encontrado", 404)
    try:
        new_status = UserStatus(validated_json()["status"])
    except ValueError:
        return error("Estado inválido")
    if target.id == actor.id and new_status != UserStatus.ACTIVE:
        return error("No puede inhabilitar su propia cuenta")
    if target.role == Role.SUPERADMIN and new_status != UserStatus.ACTIVE:
        active = db.session.scalar(
            select(func.count()).select_from(User).where(
                User.role == Role.SUPERADMIN,
                User.status == UserStatus.ACTIVE,
                User.deleted_at.is_(None),
            )
        )
        if active <= 1:
            return error("No puede inhabilitar al último SUPERADMIN activo")
    target.status = new_status
    if new_status == UserStatus.ACTIVE:
        target.failed_login_attempts = 0
    audit("CAMBIAR_ESTADO", "Usuario", target.id, f"Estado {new_status.value}")
    db.session.commit()
    return {"message": "Estado actualizado", "data": admin_user_json(target)}


@admin_bp.delete("/admin/users/<uuid:user_id>")
@roles(Role.SUPERADMIN)
def delete_admin_user(user_id):
    target = db.session.get(User, user_id)
    actor = current_user()
    if not target or target.deleted_at or target.role == Role.EXPOSITOR:
        return error("Administrador no encontrado", 404)
    if target.id == actor.id:
        return error("No puede eliminar su propia cuenta", 409)
    if target.role == Role.SUPERADMIN:
        active = db.session.scalar(
            select(func.count()).select_from(User).where(
                User.role == Role.SUPERADMIN,
                User.status == UserStatus.ACTIVE,
                User.deleted_at.is_(None),
            )
        )
        if active <= 1:
            return error("No puede eliminar al último SUPERADMIN activo", 409)
    target.deleted_at = datetime.now(timezone.utc)
    target.status = UserStatus.INACTIVE
    audit("ELIMINAR", "Usuario", target.id, "Eliminación lógica de administrador")
    db.session.commit()
    return "", 204


@admin_bp.post("/admin/users/<uuid:user_id>/reset-password")
@roles(Role.SUPERADMIN)
def admin_reset_password(user_id):
    user = db.session.get(User, user_id)
    if not user or user.deleted_at:
        return error("Usuario no encontrado", 404)
    password = temporary_password()
    user.set_password(password)
    user.must_change_password = True
    user.status = UserStatus.ACTIVE
    user.failed_login_attempts = 0
    user.password_changed_at = datetime.now(timezone.utc)
    audit("RESTABLECER_CONTRASENA", "Usuario", user.id, "Restablecimiento administrativo")
    db.session.commit()
    delivery = deliver_credentials(user, password)
    response = {"message": "Contraseña restablecida", "email_sent": delivery.get("sent", False)}
    if not BrevoEmailService().enabled:
        response["temporary_password"] = password
    return response


@admin_bp.get("/audit")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def list_audit():
    def serialize(item):
        return {
            "id": str(item.id),
            "accion": item.accion,
            "entidad": item.entidad,
            "entidad_id": str(item.entidad_id) if item.entidad_id else None,
            "descripcion": item.descripcion,
            "created_at": item.created_at.isoformat(),
        }

    return paginate(select(Audit).order_by(Audit.created_at.desc()), serialize)
