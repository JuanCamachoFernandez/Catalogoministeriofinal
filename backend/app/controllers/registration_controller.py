from datetime import datetime, timezone
import secrets
import string
from pathlib import Path
import shutil
import uuid

from flask import Blueprint, current_app, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..email_service import BrevoEmailService, EmailDeliveryError
from ..extensions import db
from ..models import (
    NotificationStatus,
    ProductiveSector,
    ProductiveUnit,
    ProductiveUnitStatus,
    RegistrationRequest,
    RegistrationRequestSector,
    RegistrationStatus,
    Role,
    SectorStatus,
    UnitSector,
    User,
    UserStatus,
)
from ..views import error, paginate, validate_json, validated_json
from ..views.domain_serializers import registration_request_json
from ..views.registration_request_view import (
    ApproveRegistrationRequestSchema,
    RegistrationRequestSchema,
    RejectRegistrationRequestSchema,
)
from .common import audit, current_user, require_managed_upload, roles, save_upload, unique_username

registration_bp = Blueprint("registration_requests", __name__)
ADMIN_ROLES = (Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO, Role.ADMIN)


def _clean(value):
    return value.strip() if isinstance(value, str) else value


def _validated_sector_rows(items):
    seen = set()
    rows = []
    for data in items:
        sector_id = data["productive_sector_id"]
        if sector_id in seen:
            raise ValueError("No se permiten sectores duplicados")
        seen.add(sector_id)
        sector = db.session.get(ProductiveSector, sector_id)
        if not sector or sector.deleted_at or sector.estado != SectorStatus.ACTIVE:
            raise ValueError("Uno de los sectores no está disponible")
        detail = _clean(data.get("detalle_otro")) or None
        if sector.es_otro and not detail:
            raise ValueError("detalle_otro es obligatorio para el sector Otros")
        if not sector.es_otro and detail:
            raise ValueError("detalle_otro solo corresponde al sector Otros")
        rows.append((sector, detail))
    return rows


@registration_bp.post("/registration-requests/logo")
def upload_registration_logo():
    try:
        url = save_upload(request.files.get("file"), "solicitudes")
    except ValueError as exc:
        return error(str(exc))
    if not url:
        return error("Debe enviar una imagen")
    return {"logo_url": url}, 201


@registration_bp.post("/registration-requests")
@validate_json(RegistrationRequestSchema())
def create_registration_request():
    data = validated_json()
    email = data["correo_electronico"].lower().strip()
    nit = _clean(data.get("nit")) or None
    if data.get("logo_url"):
        try:
            require_managed_upload(data["logo_url"], "solicitudes")
        except ValueError as exc:
            return error(str(exc))
    if db.session.scalar(
        select(RegistrationRequest.id).where(
            RegistrationRequest.correo_electronico == email,
            RegistrationRequest.estado == RegistrationStatus.PENDING,
        )
    ):
        return error("Ya existe una solicitud pendiente para este correo", 409)
    if db.session.scalar(select(User.id).where(User.email == email)) or db.session.scalar(
        select(ProductiveUnit.id).where(
            ProductiveUnit.correo_electronico == email,
            ProductiveUnit.deleted_at.is_(None),
        )
    ):
        return error("El correo ya está registrado", 409)
    if nit and (
        db.session.scalar(select(ProductiveUnit.id).where(ProductiveUnit.nit == nit))
        or db.session.scalar(
            select(RegistrationRequest.id).where(
                RegistrationRequest.nit == nit,
                RegistrationRequest.estado == RegistrationStatus.PENDING,
            )
        )
    ):
        return error("El NIT ya está registrado", 409)
    try:
        sectors = _validated_sector_rows(data.pop("sectores"))
        item = RegistrationRequest(
            **{
                key: _clean(value)
                for key, value in data.items()
                if key not in {"correo_electronico", "nit"}
            },
            correo_electronico=email,
            nit=nit,
            estado=RegistrationStatus.PENDING,
        )
        db.session.add(item)
        db.session.flush()
        db.session.add_all(
            RegistrationRequestSector(
                registration_request_id=item.id,
                productive_sector_id=sector.id,
                detalle_otro=detail,
            )
            for sector, detail in sectors
        )
        audit("CREAR_SOLICITUD", "RegistrationRequest", item.id)
        db.session.commit()
    except (ValueError, IntegrityError) as exc:
        db.session.rollback()
        message = "La solicitud contiene datos duplicados" if isinstance(exc, IntegrityError) else str(exc)
        return error(message, 409 if isinstance(exc, IntegrityError) else 400)
    return registration_request_json(item), 201


@registration_bp.get("/admin/registration-requests")
@roles(*ADMIN_ROLES)
def list_registration_requests():
    query = select(RegistrationRequest)
    state = request.args.get("estado")
    department = request.args.get("departamento")
    term = (request.args.get("q") or "").strip()
    sector_id = request.args.get("sector_id")
    if state:
        try:
            query = query.where(RegistrationRequest.estado == RegistrationStatus(state))
        except ValueError:
            return error("Estado inválido")
    if department:
        query = query.where(RegistrationRequest.departamento == department)
    if term:
        query = query.where(
            RegistrationRequest.nombre_comercial.ilike(f"%{term}%")
            | RegistrationRequest.razon_social.ilike(f"%{term}%")
            | RegistrationRequest.correo_electronico.ilike(f"%{term}%")
        )
    if sector_id:
        query = query.join(RegistrationRequestSector).where(
            RegistrationRequestSector.productive_sector_id == sector_id
        )
    return paginate(query.order_by(RegistrationRequest.created_at.desc()), registration_request_json)


@registration_bp.get("/admin/registration-requests/<uuid:request_id>")
@roles(*ADMIN_ROLES)
def get_registration_request(request_id):
    item = db.session.get(RegistrationRequest, request_id)
    return registration_request_json(item) if item else error("Solicitud no encontrada", 404)


def _temporary_password():
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "A1!" + "".join(secrets.choice(alphabet) for _ in range(13))


def _send_credentials(item, user, password):
    try:
        result = BrevoEmailService().send_temporary_credentials(
            item.correo_electronico, item.nombre_representante, user.username, password
        )
        item.notification_status = NotificationStatus.SENT if result.get("sent") else NotificationStatus.PENDING
        if result.get("sent"):
            item.credentials_sent_at = datetime.now(timezone.utc)
        audit(
            "ENVIAR_CREDENCIALES",
            "RegistrationRequest",
            item.id,
            result="SUCCESS" if result.get("sent") else "PENDING",
        )
    except EmailDeliveryError:
        current_app.logger.exception("No se pudieron enviar las credenciales")
        item.notification_status = NotificationStatus.FAILED
        audit(
            "ENVIAR_CREDENCIALES",
            "RegistrationRequest",
            item.id,
            result="FAILED",
        )
    db.session.commit()


def _stage_request_logo(item):
    if not item.logo_url:
        return None
    source = require_managed_upload(item.logo_url, "solicitudes")
    target_folder = Path(current_app.config["CARPETA_CARGAS"]) / "unidades_productivas"
    target_folder.mkdir(parents=True, exist_ok=True)
    target = target_folder / f"{uuid.uuid4().hex}{source.suffix.lower()}"
    shutil.copy2(source, target)
    return source, target, f"/uploads/unidades_productivas/{target.name}"


@registration_bp.post("/admin/registration-requests/<uuid:request_id>/approve")
@roles(*ADMIN_ROLES)
@validate_json(ApproveRegistrationRequestSchema())
def approve_registration_request(request_id):
    item = db.session.scalar(
        select(RegistrationRequest).where(RegistrationRequest.id == request_id).with_for_update()
    )
    if not item:
        return error("Solicitud no encontrada", 404)
    if item.estado != RegistrationStatus.PENDING:
        return error("La solicitud ya fue revisada", 409)
    links = db.session.scalars(
        select(RegistrationRequestSector).where(
            RegistrationRequestSector.registration_request_id == item.id
        )
    ).all()
    try:
        sectors = _validated_sector_rows(
            [
                {"productive_sector_id": link.productive_sector_id, "detalle_otro": link.detalle_otro}
                for link in links
            ]
        )
    except ValueError as exc:
        return error(str(exc), 409)
    if not sectors:
        return error("La solicitud debe tener al menos un sector activo", 409)
    email = item.correo_electronico.lower()
    if db.session.scalar(select(User.id).where(User.email == email)) or db.session.scalar(
        select(ProductiveUnit.id).where(ProductiveUnit.correo_electronico == email)
    ):
        return error("El correo ya está registrado", 409)
    if item.nit and db.session.scalar(select(ProductiveUnit.id).where(ProductiveUnit.nit == item.nit)):
        return error("El NIT ya está registrado", 409)
    password = _temporary_password()
    words = item.nombre_representante.split(maxsplit=1)
    user = User(
        username=unique_username(words[0], words[1] if len(words) > 1 else "unidad"),
        email=email,
        role=Role.PRODUCTIVE_UNIT_RESPONSIBLE,
        first_name=words[0],
        last_name=words[1] if len(words) > 1 else "",
        phone=item.telefono_whatsapp,
        status=UserStatus.ACTIVE,
        must_change_password=True,
    )
    user.set_password(password)
    logo_transfer = None
    try:
        logo_transfer = _stage_request_logo(item)
        db.session.add(user)
        db.session.flush()
        unit = ProductiveUnit(
            user_id=user.id,
            registration_request_id=item.id,
            nombre_comercial=item.nombre_comercial,
            razon_social=item.razon_social,
            nit=item.nit,
            registro_seprec=item.registro_seprec,
            registro_pro_bolivia=item.registro_pro_bolivia,
            nombre_representante=item.nombre_representante,
            departamento=item.departamento,
            direccion_fisica=item.direccion_fisica,
            telefono_whatsapp=item.telefono_whatsapp,
            correo_electronico=email,
            facebook_url=item.facebook_url,
            instagram_url=item.instagram_url,
            tiktok_url=item.tiktok_url,
            resena_comercial=item.resena_comercial,
            logo_url=logo_transfer[2] if logo_transfer else None,
            estado=ProductiveUnitStatus.ACTIVE,
            fecha_aprobacion=datetime.now(timezone.utc),
        )
        db.session.add(unit)
        db.session.flush()
        db.session.add_all(
            UnitSector(
                productive_unit_id=unit.id,
                productive_sector_id=sector.id,
                detalle_otro=detail,
            )
            for sector, detail in sectors
        )
        item.estado = RegistrationStatus.APPROVED
        item.fecha_revision = datetime.now(timezone.utc)
        item.reviewed_by = current_user().id
        item.observaciones = validated_json().get("observaciones")
        item.notification_status = NotificationStatus.PENDING
        if logo_transfer:
            item.logo_url = logo_transfer[2]
        audit("APROBAR_SOLICITUD", "RegistrationRequest", item.id)
        db.session.commit()
    except (IntegrityError, OSError, ValueError) as exc:
        db.session.rollback()
        if logo_transfer and logo_transfer[1].is_file():
            logo_transfer[1].unlink()
        current_app.logger.warning("No fue posible aprobar la solicitud %s", item.id)
        return error("No fue posible aprobar la solicitud", 409)
    if logo_transfer and logo_transfer[0].is_file():
        logo_transfer[0].unlink()
    _send_credentials(item, user, password)
    return registration_request_json(item)


@registration_bp.post("/admin/registration-requests/<uuid:request_id>/reject")
@roles(*ADMIN_ROLES)
@validate_json(RejectRegistrationRequestSchema())
def reject_registration_request(request_id):
    item = db.session.get(RegistrationRequest, request_id)
    if not item:
        return error("Solicitud no encontrada", 404)
    if item.estado != RegistrationStatus.PENDING:
        return error("La solicitud ya fue revisada", 409)
    data = validated_json()
    item.estado = RegistrationStatus.REJECTED
    item.motivo_rechazo = data["motivo"].strip()
    item.observaciones = data.get("observaciones")
    item.fecha_revision = datetime.now(timezone.utc)
    item.reviewed_by = current_user().id
    item.notification_status = NotificationStatus.PENDING
    audit("RECHAZAR_SOLICITUD", "RegistrationRequest", item.id)
    db.session.commit()
    try:
        result = BrevoEmailService().send_registration_rejected(
            item.correo_electronico, item.nombre_representante, item.motivo_rechazo
        )
        item.notification_status = NotificationStatus.SENT if result.get("sent") else NotificationStatus.PENDING
        audit(
            "ENVIAR_RECHAZO",
            "RegistrationRequest",
            item.id,
            result="SUCCESS" if result.get("sent") else "PENDING",
        )
    except EmailDeliveryError:
        item.notification_status = NotificationStatus.FAILED
        audit(
            "ENVIAR_RECHAZO",
            "RegistrationRequest",
            item.id,
            result="FAILED",
        )
    db.session.commit()
    return registration_request_json(item)


@registration_bp.post("/admin/registration-requests/<uuid:request_id>/resend-credentials")
@roles(*ADMIN_ROLES)
def resend_credentials(request_id):
    item = db.session.get(RegistrationRequest, request_id)
    if not item or item.estado != RegistrationStatus.APPROVED:
        return error("Solicitud aprobada no encontrada", 404)
    unit = db.session.scalar(select(ProductiveUnit).where(ProductiveUnit.registration_request_id == item.id))
    user = db.session.get(User, unit.user_id) if unit else None
    if not user:
        return error("La cuenta asociada no existe", 409)
    password = _temporary_password()
    user.set_password(password)
    user.must_change_password = True
    user.token_version += 1
    db.session.commit()
    _send_credentials(item, user, password)
    audit("REENVIAR_CREDENCIALES", "RegistrationRequest", item.id)
    db.session.commit()
    return {"message": "Credenciales regeneradas", "notification_status": item.notification_status.value}
