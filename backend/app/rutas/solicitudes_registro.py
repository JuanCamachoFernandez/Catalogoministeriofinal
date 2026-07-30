from datetime import date, datetime, timezone
import secrets
import string

from flask import Blueprint, current_app, request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..servicios.servicio_correo import BrevoEmailService, EmailDeliveryError
from ..extensiones import db
from ..modelos import (
    NotificationStatus,
    ProductiveSector,
    Product,
    ProductImage,
    ProductStatus,
    ProductiveUnit,
    ProductiveUnitStatus,
    RegistrationRequest,
    RegistrationRequestProduct,
    RegistrationRequestSector,
    RegistrationStatus,
    Role,
    SectorStatus,
    UnitSector,
    User,
    UserStatus,
)
from ..utilidades import slugify
from ..esquemas import error, paginate, validate_json, validated_json
from ..serializadores.dominio import registration_request_json
from ..esquemas.solicitudes_registro import (
    ApproveRegistrationRequestSchema,
    RegistrationRequestSchema,
    RejectRegistrationRequestSchema,
)
from ..servicios import (
    audit,
    cloudinary_public_id_from_url,
    delete_cloudinary_upload,
    delete_managed_upload,
    unique_username,
    upload_to_cloudinary,
    validate_image_reference,
)

from ..autenticacion.decoradores import roles
from ..autenticacion.sesiones import current_user
from ..autenticacion.permisos import ROLES_ADMINISTRACION_COMPLETA
registration_bp = Blueprint("registration_requests", __name__)


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
        uploaded = upload_to_cloudinary(request.files.get("file"), "solicitudes")
    except ValueError as exc:
        return error(str(exc))
    if not uploaded:
        return error("Debe enviar una imagen")
    return {
        "logo_url": uploaded["url"],
        "url": uploaded["url"],
    }, 201


@registration_bp.post("/registration-requests/products/image")
def upload_registration_product_image():
    try:
        uploaded = upload_to_cloudinary(request.files.get("file"), "solicitudes")
    except ValueError as exc:
        return error(str(exc))
    if not uploaded:
        return error("Debe enviar una imagen")
    return {
        "imagen_url": uploaded["url"],
        "url": uploaded["url"],
    }, 201


@registration_bp.post("/registration-requests")
@validate_json(RegistrationRequestSchema())
def create_registration_request():
    data = validated_json()
    email = data["correo_electronico"].lower().strip()
    nit = _clean(data.get("nit")) or None
    try:
        validate_image_reference(data["logo_url"], "solicitudes")
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
        products = data.pop("productos")
        for product in products:
            validate_image_reference(product["imagen_url"], "solicitudes")
        item = RegistrationRequest(
            **{
                key: _clean(value)
                for key, value in data.items()
                if key not in {"correo_electronico", "nit"}
            },
            correo_electronico=email,
            nit=nit,
            logo_public_id=cloudinary_public_id_from_url(data["logo_url"], "solicitudes"),
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
        db.session.add_all(
            RegistrationRequestProduct(
                registration_request_id=item.id,
                nombre_comercial=_clean(product["nombre_comercial"]),
                descripcion_tecnica=_clean(product["descripcion_tecnica"]),
                precio_referencia=product["precio_referencia"],
                imagen_url=product["imagen_url"],
                orden=index,
            )
            for index, product in enumerate(products)
        )
        audit("CREAR_SOLICITUD", "RegistrationRequest", item.id)
        db.session.commit()
    except (ValueError, IntegrityError) as exc:
        db.session.rollback()
        message = "La solicitud contiene datos duplicados" if isinstance(exc, IntegrityError) else str(exc)
        return error(message, 409 if isinstance(exc, IntegrityError) else 400)
    return registration_request_json(item), 201


@registration_bp.get("/admin/registration-requests")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
def list_registration_requests():
    query = select(RegistrationRequest)
    state = request.args.get("estado")
    department = request.args.get("departamento")
    term = (request.args.get("q") or "").strip()
    sector_id = request.args.get("sector_id")
    try:
        date_from = (
            date.fromisoformat(request.args["date_from"])
            if request.args.get("date_from")
            else None
        )
        date_to = (
            date.fromisoformat(request.args["date_to"])
            if request.args.get("date_to")
            else None
        )
    except ValueError:
        return error("Rango de fechas inválido")
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
    if date_from:
        query = query.where(func.date(RegistrationRequest.created_at) >= date_from)
    if date_to:
        query = query.where(func.date(RegistrationRequest.created_at) <= date_to)
    return paginate(query.order_by(RegistrationRequest.created_at.desc()), registration_request_json)


@registration_bp.get("/admin/registration-requests/<uuid:request_id>")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
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
    return {
        "url": item.logo_url,
        "public_id": item.logo_public_id
        or cloudinary_public_id_from_url(item.logo_url, "solicitudes"),
    }


def _stage_request_product_image(image_url):
    return {
        "url": image_url,
        "public_id": cloudinary_public_id_from_url(image_url, "solicitudes"),
    }


def _delete_image_reference(url, public_id, folder):
    if public_id:
        delete_cloudinary_upload(public_id)
    elif url:
        delete_managed_upload(url, folder)


def _delete_request_media(item):
    if item.logo_url:
        _delete_image_reference(item.logo_url, item.logo_public_id, "solicitudes")
        item.logo_url = None
        item.logo_public_id = None
    products = db.session.scalars(
        select(RegistrationRequestProduct).where(
            RegistrationRequestProduct.registration_request_id == item.id
        )
    ).all()
    for product in products:
        _delete_image_reference(
            product.imagen_url,
            cloudinary_public_id_from_url(product.imagen_url, "solicitudes"),
            "solicitudes",
        )
        db.session.delete(product)


@registration_bp.post("/admin/registration-requests/<uuid:request_id>/approve")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
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
    request_products = db.session.scalars(
        select(RegistrationRequestProduct)
        .where(RegistrationRequestProduct.registration_request_id == item.id)
        .order_by(RegistrationRequestProduct.orden, RegistrationRequestProduct.created_at)
    ).all()
    if len(request_products) != 3:
        return error("La solicitud debe incluir exactamente tres productos", 409)
    email = item.correo_electronico.lower()
    if db.session.scalar(select(User.id).where(User.email == email)) or db.session.scalar(
        select(ProductiveUnit.id).where(ProductiveUnit.correo_electronico == email)
    ):
        return error("El correo ya está registrado", 409)
    if item.nit and db.session.scalar(select(ProductiveUnit.id).where(ProductiveUnit.nit == item.nit)):
        return error("El NIT ya está registrado", 409)
    password = _temporary_password()
    user = User(
        username=unique_username(
            item.nombres_representante, item.apellido_paterno_representante
        ),
        email=email,
        role=Role.PRODUCTIVE_UNIT_RESPONSIBLE,
        first_name=item.nombres_representante,
        last_name=item.apellido_paterno_representante,
        apellido_paterno=item.apellido_paterno_representante,
        apellido_materno=item.apellido_materno_representante,
        phone=item.telefono_whatsapp,
        status=UserStatus.ACTIVE,
        must_change_password=True,
    )
    user.set_password(password)
    logo_transfer = None
    product_transfers = []
    try:
        logo_transfer = _stage_request_logo(item)
        for requested_product in request_products:
            product_transfers.append(
                (requested_product, _stage_request_product_image(requested_product.imagen_url))
            )
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
            nombres_representante=item.nombres_representante,
            apellido_paterno_representante=item.apellido_paterno_representante,
            apellido_materno_representante=item.apellido_materno_representante,
            departamento=item.departamento,
            direccion_fisica=item.direccion_fisica,
            telefono_whatsapp=item.telefono_whatsapp,
            correo_electronico=email,
            facebook_url=item.facebook_url,
            instagram_url=item.instagram_url,
            tiktok_url=item.tiktok_url,
            resena_comercial=item.resena_comercial,
            logo_url=logo_transfer["url"] if logo_transfer else None,
            logo_public_id=logo_transfer["public_id"] if logo_transfer else None,
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
        for requested_product, transfer in product_transfers:
            product = Product(
                productive_unit_id=unit.id,
                estado=ProductStatus.DRAFT,
            )
            product.nombre_comercial = requested_product.nombre_comercial
            product.descripcion_tecnica = requested_product.descripcion_tecnica
            product.materia_prima = "Pendiente de completar"
            product.presentacion_empaque = "Pendiente de completar"
            product.precio_referencia = requested_product.precio_referencia
            product.capacidad_produccion_stock = "Pendiente de completar"
            product.nombre = requested_product.nombre_comercial
            product.descripcion = requested_product.descripcion_tecnica
            product.materiales_o_ingredientes = "Pendiente de completar"
            product.presentacion = "Pendiente de completar"
            product.precio = requested_product.precio_referencia
            product.slug = slugify(requested_product.nombre_comercial)
            db.session.add(product)
            db.session.flush()
            db.session.add(
                ProductImage(
                    product_id=product.id,
                    filename=requested_product.imagen_url.rsplit("/", 1)[-1].split("?", 1)[0],
                    url=transfer["url"],
                    public_id=transfer["public_id"],
                    alt_text=f"Imagen de {requested_product.nombre_comercial}",
                    is_cover=True,
                    display_order=0,
                )
            )
            requested_product.imagen_url = transfer["url"]
        item.estado = RegistrationStatus.APPROVED
        item.fecha_revision = datetime.now(timezone.utc)
        item.reviewed_by = current_user().id
        item.observaciones = validated_json().get("observaciones")
        item.notification_status = NotificationStatus.PENDING
        if logo_transfer:
            item.logo_url = logo_transfer["url"]
            item.logo_public_id = logo_transfer["public_id"]
        audit("APROBAR_SOLICITUD", "RegistrationRequest", item.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        current_app.logger.warning("No fue posible aprobar la solicitud %s", item.id)
        return error("No fue posible aprobar la solicitud", 409)
    _send_credentials(item, user, password)
    return registration_request_json(item)


@registration_bp.post("/admin/registration-requests/<uuid:request_id>/reject")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
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
    _delete_request_media(item)
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
@roles(*ROLES_ADMINISTRACION_COMPLETA)
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
