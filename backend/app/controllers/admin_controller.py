from datetime import datetime, timezone

from flask import Blueprint, request
from sqlalchemy import func, select

from ..extensions import db
from ..models import (
    AdminProfile,
    AdminUnit,
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
from ..utils import document_initial_password, valid_gmail
from ..views import admin_user_json, error, paginate, validate_json, validated_json
from ..views.admin_view import AdminCreateSchema, AdminUpdateSchema, UserStatusSchema
from .auth_controller import strong_password
from .common import (
    audit,
    audit_description,
    current_user,
    delete_managed_upload,
    require_managed_upload,
    roles,
    unique_username,
)

admin_bp = Blueprint("admin", __name__)


def ensure_admin_unit(value):
    name = (value or "").strip()
    if not name:
        return None
    existing = db.session.scalar(
        select(AdminUnit).where(func.lower(AdminUnit.nombre) == name.lower())
    )
    if existing:
        return existing.nombre
    db.session.add(AdminUnit(nombre=name))
    return name


@admin_bp.get("/admin/units")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def list_admin_units():
    units = db.session.scalars(select(AdminUnit).order_by(AdminUnit.nombre)).all()
    return {"items": [{"id": str(item.id), "nombre": item.nombre} for item in units]}


@admin_bp.get("/admin/profile")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def own_admin_profile():
    return admin_user_json(current_user())


@admin_bp.patch("/admin/profile")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(AdminUpdateSchema())
def update_own_admin_profile():
    user = current_user()
    data = validated_json()
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
    if "apellido_paterno" not in data:
        data["apellido_paterno"] = data.get("paternal_last_name") or data.get("last_name")
    if "apellido_materno" not in data and "maternal_last_name" in data:
        data["apellido_materno"] = data["maternal_last_name"]
    for field in ("first_name", "apellido_paterno", "apellido_materno", "phone"):
        if field in data:
            setattr(user, field, data.get(field))
    if data.get("apellido_paterno"):
        user.last_name = data["apellido_paterno"]
    profile = user.admin_profile
    if not profile:
        profile = AdminProfile(user_id=user.id)
        db.session.add(profile)
    if "numero_documento" in data:
        numero_documento = (data.get("numero_documento") or "").strip()
        duplicate = db.session.scalar(
            select(AdminProfile.id).where(
                AdminProfile.numero_documento == numero_documento,
                AdminProfile.user_id != user.id,
            )
        ) or db.session.scalar(
            select(Exhibitor.id).where(Exhibitor.numero_documento == numero_documento)
        )
        if duplicate:
            return error("El número de documento ya está registrado", 409)
        profile.numero_documento = numero_documento
    for field in ("cargo", "unidad", "observaciones"):
        if field in data:
            value = ensure_admin_unit(data.get(field)) if field == "unidad" else data.get(field)
            setattr(profile, field, value)
    old_photo = None
    if "foto_perfil" in data and data.get("foto_perfil") != user.foto_perfil:
        try:
            if data.get("foto_perfil"):
                require_managed_upload(data["foto_perfil"], "perfiles")
        except ValueError as exc:
            return error(str(exc))
        old_photo = user.foto_perfil
        user.foto_perfil = data.get("foto_perfil")
    audit("EDITAR", "Perfil", user.id, f"Perfil actualizado por {user.username}")
    db.session.commit()
    if old_photo:
        delete_managed_upload(old_photo, "perfiles")
    return admin_user_json(user)


@admin_bp.delete("/admin/units/<uuid:unit_id>")
@roles(Role.SUPERADMIN)
def delete_admin_unit(unit_id):
    unit = db.session.get(AdminUnit, unit_id)
    if not unit:
        return error("Unidad no encontrada", 404)
    db.session.delete(unit)
    audit("ELIMINAR", "Unidad", unit.id, f"Unidad eliminada: {unit.nombre}")
    db.session.commit()
    return "", 204


@admin_bp.get("/admin/dashboard")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def admin_dashboard():
    from .fair_controller import sync_fair_lifecycle

    sync_fair_lifecycle()
    count = lambda model, *conditions: db.session.scalar(
        select(func.count()).select_from(model).where(*conditions)
    ) or 0
    audits = db.session.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(8)).all()
    return {
        "stats": {
            "ferias": count(Fair, Fair.deleted_at.is_(None)),
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
                "descripcion": item.descripcion or audit_description(item.accion, item.entidad),
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
    if request.args.get("status") in {item.value for item in UserStatus}:
        query = query.where(User.status == UserStatus(request.args["status"]))
    if request.args.get("role") in {
        Role.SUPERADMIN.value,
        Role.ADMIN_VICEMINISTERIO.value,
    }:
        query = query.where(User.role == Role(request.args["role"]))
    if request.args.get("unit"):
        query = query.join(AdminProfile).where(AdminProfile.unidad == request.args["unit"])
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
    apellido_paterno = (
        data.get("apellido_paterno")
        or data.get("paternal_last_name")
        or data.get("last_name")
    )
    apellido_materno = data.get("apellido_materno") or data.get("maternal_last_name")
    numero_documento = (data.get("numero_documento") or "").strip()
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
    if not data.get("first_name") or not apellido_paterno or not numero_documento:
        return error("Nombres, apellido paterno y número de CI son obligatorios")
    document_exists = db.session.scalar(
        select(AdminProfile.id).where(
            AdminProfile.numero_documento == numero_documento
        )
    ) or db.session.scalar(
        select(Exhibitor.id).where(Exhibitor.numero_documento == numero_documento)
    )
    if document_exists:
        return error("El número de documento ya está registrado", 409)
    password = document_initial_password(
        numero_documento, data["first_name"], apellido_paterno
    )
    unit_name = ensure_admin_unit(data.get("unidad"))
    user = User(
        username=unique_username(data["first_name"], apellido_paterno),
        email=email,
        role=role,
        first_name=data["first_name"].strip(),
        # Se conserva last_name para los flujos antiguos y los usuarios expositores.
        last_name=apellido_paterno.strip(),
        apellido_paterno=apellido_paterno.strip(),
        apellido_materno=(
            apellido_materno.strip() if apellido_materno else None
        ),
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
            numero_documento=numero_documento,
            cargo=data.get("cargo"),
            unidad=unit_name,
            observaciones=data.get("observaciones"),
        )
    )
    audit("CREAR", "Usuario", user.id, f"Administrador creado: {user.username}")
    db.session.commit()
    response = {
        "message": "Administrador creado",
        "data": admin_user_json(user),
        "username": user.username,
        "temporary_password": password,
    }
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
    if "apellido_paterno" not in data:
        data["apellido_paterno"] = data.get("paternal_last_name") or data.get("last_name")
    if "apellido_materno" not in data and "maternal_last_name" in data:
        data["apellido_materno"] = data["maternal_last_name"]
    for field in ("first_name", "apellido_paterno", "apellido_materno", "phone"):
        if field in data:
            setattr(user, field, data.get(field))
    if data.get("apellido_paterno"):
        user.last_name = data["apellido_paterno"]
    if user.admin_profile:
        if "numero_documento" in data:
            numero_documento = (data.get("numero_documento") or "").strip()
            duplicate = db.session.scalar(
                select(AdminProfile.id).where(
                    AdminProfile.numero_documento == numero_documento,
                    AdminProfile.id != user.admin_profile.id,
                )
            ) or db.session.scalar(
                select(Exhibitor.id).where(
                    Exhibitor.numero_documento == numero_documento
                )
            )
            if duplicate:
                return error("El número de documento ya está registrado", 409)
            user.admin_profile.numero_documento = numero_documento
        for field in ("cargo", "unidad", "observaciones"):
            if field in data:
                value = ensure_admin_unit(data.get(field)) if field == "unidad" else data.get(field)
                setattr(user.admin_profile, field, value)
    audit("EDITAR", "Usuario", user.id, f"Administrador actualizado: {user.username}")
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
    audit(
        "CAMBIAR_ESTADO",
        "Usuario",
        target.id,
        f"Estado de {target.username} cambiado a {new_status.value}",
    )
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
    audit("ELIMINAR", "Usuario", target.id, f"Administrador eliminado: {target.username}")
    db.session.commit()
    return "", 204


@admin_bp.post("/admin/users/<uuid:user_id>/reset-password")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def admin_reset_password(user_id):
    user = db.session.get(User, user_id)
    actor = current_user()
    if not user or user.deleted_at:
        return error("Usuario no encontrado", 404)
    if actor.role == Role.ADMIN_VICEMINISTERIO and user.role != Role.EXPOSITOR:
        return error(
            "Un administrador solo puede restablecer contraseñas de expositores",
            403,
        )
    if user.role == Role.EXPOSITOR and user.exhibitor:
        document = user.exhibitor.numero_documento
        first_name = user.exhibitor.nombre_responsable
        last_name = user.exhibitor.apellido_responsable
    elif user.admin_profile and user.admin_profile.numero_documento:
        document = user.admin_profile.numero_documento
        first_name = user.first_name
        last_name = user.apellido_paterno or user.last_name
    else:
        return error("Registre el número de documento antes de restablecer", 409)
    password = document_initial_password(document, first_name, last_name)
    user.set_password(password)
    user.must_change_password = True
    user.status = UserStatus.ACTIVE
    user.failed_login_attempts = 0
    user.password_changed_at = datetime.now(timezone.utc)
    audit(
        "RESTABLECER_CONTRASENA",
        "Usuario",
        user.id,
        f"Contraseña restablecida para {user.username}",
    )
    db.session.commit()
    return {
        "message": "Contraseña restablecida",
        "username": user.username,
        "temporary_password": password,
    }


@admin_bp.get("/audit")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def list_audit():
    def serialize(item):
        actor = db.session.get(User, item.user_id) if item.user_id else None
        return {
            "id": str(item.id),
            "accion": item.accion,
            "entidad": item.entidad,
            "entidad_id": str(item.entidad_id) if item.entidad_id else None,
            "descripcion": item.descripcion or audit_description(item.accion, item.entidad),
            "usuario": actor.username if actor else "Sistema",
            "created_at": item.created_at.isoformat(),
        }

    query = select(Audit)
    term = request.args.get("q", "").strip()
    if term:
        pattern = f"%{term}%"
        query = query.outerjoin(User, Audit.user_id == User.id).where(
            Audit.accion.ilike(pattern)
            | Audit.entidad.ilike(pattern)
            | Audit.descripcion.ilike(pattern)
            | User.username.ilike(pattern)
        )
    if request.args.get("action"):
        query = query.where(Audit.accion == request.args["action"])
    if request.args.get("entity"):
        query = query.where(Audit.entidad == request.args["entity"])
    if request.args.get("date_from"):
        query = query.where(func.date(Audit.created_at) >= request.args["date_from"])
    if request.args.get("date_to"):
        query = query.where(func.date(Audit.created_at) <= request.args["date_to"])
    return paginate(query.order_by(Audit.created_at.desc()), serialize)
