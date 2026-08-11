from datetime import datetime, timezone
from uuid import UUID

from flask import Blueprint, current_app, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..extensiones import db
from ..modelos import (
    Fair,
    FairParticipation,
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
from ..esquemas import error, paginate, validate_json, validated_json
from ..serializadores.dominio import productive_unit_json
from ..esquemas.unidades_productivas import (
    AdminProductiveUnitCreateSchema,
    ProductiveUnitStatusSchema,
    ProductiveUnitUpdateSchema,
    UnitSectorsSchema,
)
from ..servicios import (
    audit,
    delete_cloudinary_upload,
    delete_managed_upload,
    invalidate_public_cache,
    unique_username,
    upload_to_cloudinary,
    validate_image_reference,
)
from .solicitudes_registro import (
    _send_credentials,
    _stage_request_logo,
    _temporary_password,
    _validated_sector_rows,
)

from ..autenticacion.decoradores import roles
from ..autenticacion.sesiones import current_user
from ..autenticacion.permisos import (
    ROLES_ADMINISTRACION_COMPLETA,
    ROLES_RESPONSABLES_UNIDAD,
)
productive_unit_bp = Blueprint("productive_units", __name__)


def _delete_unit_logo(url, public_id):
    if public_id:
        delete_cloudinary_upload(public_id)
    elif url:
        delete_managed_upload(url, "unidades_productivas")


def current_productive_unit():
    user = current_user()
    return db.session.scalar(
        select(ProductiveUnit).where(
            ProductiveUnit.user_id == user.id, ProductiveUnit.deleted_at.is_(None)
        )
    ) if user else None


def _get_available_unit(unit_id):
    item = db.session.get(ProductiveUnit, unit_id)
    return item if item and not item.deleted_at else None


def _unit_participation_json(item, fair):
    return {
        "id": str(item.id),
        "fair_id": str(item.fair_id),
        "productive_unit_id": str(item.productive_unit_id),
        "nombre_feria": fair.nombre,
        "ubicacion": fair.ubicacion or fair.lugar,
        "departamento": fair.departamento,
        "fecha_inicio": fair.fecha_inicio.isoformat(),
        "fecha_fin": fair.fecha_fin.isoformat(),
        "estado_feria": fair.estado.value,
        "estado": item.estado.value,
        "observaciones": item.observaciones,
        "fecha_registro": item.created_at.isoformat(),
        "fecha_actualizacion": item.updated_at.isoformat(),
        "authorized_at": item.authorized_at.isoformat() if item.authorized_at else None,
        "revoked_at": item.revoked_at.isoformat() if item.revoked_at else None,
    }


def _update_fields(item, data, allow_email=True):
    allowed = {
        "nombre_comercial", "razon_social", "nit", "registro_seprec",
        "registro_pro_bolivia", "nombres_representante",
        "apellido_paterno_representante", "apellido_materno_representante", "departamento",
        "direccion_fisica", "telefono_whatsapp", "facebook_url",
        "instagram_url", "tiktok_url", "resena_comercial",
    }
    if allow_email:
        allowed.add("correo_electronico")
    for key in allowed & data.keys():
        value = data[key].strip() if isinstance(data[key], str) else data[key]
        setattr(item, key, value or None if key in {"nit", "registro_seprec", "registro_pro_bolivia", "facebook_url", "instagram_url", "tiktok_url"} else value)
    if "correo_electronico" in data and allow_email:
        item.correo_electronico = data["correo_electronico"].lower().strip()
        user = db.session.get(User, item.user_id)
        user.email = item.correo_electronico
    representative_fields = {
        "nombres_representante",
        "apellido_paterno_representante",
        "apellido_materno_representante",
    }
    if representative_fields & data.keys():
        user = db.session.get(User, item.user_id)
        user.first_name = item.nombres_representante
        user.last_name = item.apellido_paterno_representante
        user.apellido_paterno = item.apellido_paterno_representante
        user.apellido_materno = item.apellido_materno_representante


@productive_unit_bp.get("/admin/productive-units")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
def list_productive_units():
    query = select(ProductiveUnit)
    sector_ids = []
    deleted_filter = request.args.get("deleted")
    if deleted_filter == "true":
        query = query.where(ProductiveUnit.deleted_at.is_not(None))
    elif deleted_filter == "false":
        query = query.where(ProductiveUnit.deleted_at.is_(None))
    elif request.args.get("include_deleted") != "true":
        query = query.where(ProductiveUnit.deleted_at.is_(None))
    if request.args.get("estado"):
        try:
            query = query.where(ProductiveUnit.estado == ProductiveUnitStatus(request.args["estado"]))
        except ValueError:
            return error("Estado inválido")
    if request.args.get("departamento"):
        query = query.where(ProductiveUnit.departamento == request.args["departamento"])
    if request.args.get("q"):
        term = request.args["q"].strip()
        query = query.where(ProductiveUnit.nombre_comercial.ilike(f"%{term}%") | ProductiveUnit.razon_social.ilike(f"%{term}%"))
    if request.args.get("sector_ids"):
        try:
            sector_ids = [
                UUID(item.strip())
                for item in request.args["sector_ids"].split(",")
                if item.strip()
            ]
        except ValueError:
            return error("Sectores inválidos")
    if sector_ids:
        query = query.join(UnitSector).where(
            UnitSector.productive_sector_id.in_(sector_ids),
            UnitSector.estado == SectorStatus.ACTIVE,
        ).distinct()
    return paginate(query.order_by(ProductiveUnit.created_at.desc()), productive_unit_json)


@productive_unit_bp.post("/admin/productive-units")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
@validate_json(AdminProductiveUnitCreateSchema())
def create_productive_unit():
    data = validated_json()
    email = data["correo_electronico"].lower().strip()
    nit = (data.get("nit") or "").strip() or None
    logo_url = (data.get("logo_url") or "").strip() or None
    if db.session.scalar(select(User.id).where(User.email == email)) or db.session.scalar(
        select(ProductiveUnit.id).where(ProductiveUnit.correo_electronico == email)
    ):
        return error("El correo ya está registrado", 409)
    if nit and db.session.scalar(select(ProductiveUnit.id).where(ProductiveUnit.nit == nit)):
        return error("El NIT ya está registrado", 409)
    try:
        sectors = _validated_sector_rows(data["sectores"])
        if logo_url:
            validate_image_reference(logo_url, "solicitudes")
    except ValueError as exc:
        return error(str(exc))

    password = _temporary_password()
    logo_transfer = None
    try:
        request_item = RegistrationRequest(
            nombre_comercial=data["nombre_comercial"].strip(),
            razon_social=data["razon_social"].strip(),
            nit=nit,
            registro_seprec=(data.get("registro_seprec") or "").strip() or None,
            registro_pro_bolivia=(data.get("registro_pro_bolivia") or "").strip() or None,
            nombres_representante=data["nombres_representante"].strip(),
            apellido_paterno_representante=data["apellido_paterno_representante"].strip(),
            apellido_materno_representante=data["apellido_materno_representante"].strip(),
            departamento=data["departamento"].strip(),
            direccion_fisica=data["direccion_fisica"].strip(),
            telefono_whatsapp=data["telefono_whatsapp"].strip(),
            correo_electronico=email,
            facebook_url=(data.get("facebook_url") or "").strip() or None,
            instagram_url=(data.get("instagram_url") or "").strip() or None,
            tiktok_url=(data.get("tiktok_url") or "").strip() or None,
            resena_comercial=data["resena_comercial"].strip(),
            logo_url=logo_url,
            logo_public_id=None,
            estado=RegistrationStatus.APPROVED,
            fecha_revision=datetime.now(timezone.utc),
            reviewed_by=current_user().id,
            notification_status=NotificationStatus.PENDING,
        )
        db.session.add(request_item)
        db.session.flush()
        db.session.add_all(
            RegistrationRequestSector(
                registration_request_id=request_item.id,
                productive_sector_id=sector.id,
                detalle_otro=detail,
            )
            for sector, detail in sectors
        )
        if logo_url:
            logo_transfer = _stage_request_logo(request_item)
        user = User(
            username=unique_username(request_item.nombres_representante, request_item.apellido_paterno_representante),
            email=email,
            role=Role.PRODUCTIVE_UNIT_RESPONSIBLE,
            first_name=request_item.nombres_representante,
            last_name=request_item.apellido_paterno_representante,
            apellido_paterno=request_item.apellido_paterno_representante,
            apellido_materno=request_item.apellido_materno_representante,
            phone=request_item.telefono_whatsapp,
            status=UserStatus.ACTIVE,
            must_change_password=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        unit = ProductiveUnit(
            user_id=user.id,
            registration_request_id=request_item.id,
            nombre_comercial=request_item.nombre_comercial,
            razon_social=request_item.razon_social,
            nit=nit,
            registro_seprec=request_item.registro_seprec,
            registro_pro_bolivia=request_item.registro_pro_bolivia,
            nombres_representante=request_item.nombres_representante,
            apellido_paterno_representante=request_item.apellido_paterno_representante,
            apellido_materno_representante=request_item.apellido_materno_representante,
            departamento=request_item.departamento,
            direccion_fisica=request_item.direccion_fisica,
            telefono_whatsapp=request_item.telefono_whatsapp,
            correo_electronico=email,
            facebook_url=request_item.facebook_url,
            instagram_url=request_item.instagram_url,
            tiktok_url=request_item.tiktok_url,
            resena_comercial=request_item.resena_comercial,
            logo_url=logo_transfer["url"] if logo_transfer else None,
            logo_public_id=logo_transfer["public_id"] if logo_transfer else None,
            estado=ProductiveUnitStatus.ACTIVE,
            fecha_aprobacion=datetime.now(timezone.utc),
        )
        request_item.logo_url = logo_transfer["url"] if logo_transfer else None
        request_item.logo_public_id = logo_transfer["public_id"] if logo_transfer else None
        db.session.add(unit)
        db.session.flush()
        db.session.add_all(
            UnitSector(productive_unit_id=unit.id, productive_sector_id=sector.id, detalle_otro=detail)
            for sector, detail in sectors
        )
        audit("CREAR_UNIDAD_PRODUCTIVA", "ProductiveUnit", unit.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        current_app.logger.exception("No fue posible crear la Unidad Productiva")
        return error("No fue posible crear la Unidad Productiva", 409)
    _send_credentials(request_item, user, password)
    invalidate_public_cache()
    return productive_unit_json(unit), 201


@productive_unit_bp.get("/admin/productive-units/<uuid:unit_id>")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
def get_productive_unit(unit_id):
    item = db.session.get(ProductiveUnit, unit_id)
    return (
        productive_unit_json(item, include_products=True)
        if item
        else error("Unidad Productiva no encontrada", 404)
    )


@productive_unit_bp.post("/admin/productive-units/<uuid:unit_id>/resend-credentials")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
def resend_productive_unit_credentials(unit_id):
    item = _get_available_unit(unit_id)
    if not item:
        return error("Unidad Productiva no encontrada", 404)
    request_item = db.session.get(RegistrationRequest, item.registration_request_id)
    user = db.session.get(User, item.user_id)
    if not request_item:
        return error("La solicitud asociada no existe", 409)
    if not user or user.deleted_at:
        return error("La cuenta asociada no existe", 409)
    password = _temporary_password()
    user.set_password(password)
    user.must_change_password = True
    user.token_version += 1
    request_item.correo_electronico = item.correo_electronico
    db.session.commit()
    _send_credentials(request_item, user, password)
    audit("REENVIAR_CREDENCIALES", "ProductiveUnit", item.id)
    db.session.commit()
    return {
        "message": "Credenciales regeneradas",
        "notification_status": request_item.notification_status.value,
    }


@productive_unit_bp.get("/admin/productive-units/<uuid:unit_id>/participations")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
def list_productive_unit_participations(unit_id):
    item = db.session.get(ProductiveUnit, unit_id)
    if not item:
        return error("Unidad Productiva no encontrada", 404)
    query = (
        select(FairParticipation, Fair)
        .join(Fair, Fair.id == FairParticipation.fair_id)
        .where(FairParticipation.productive_unit_id == unit_id)
        .order_by(Fair.fecha_inicio.desc(), Fair.created_at.desc())
    )
    rows = db.session.execute(query).all()
    return {
        "items": [
            _unit_participation_json(participation, fair)
            for participation, fair in rows
        ]
    }


@productive_unit_bp.patch("/admin/productive-units/<uuid:unit_id>")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
@validate_json(ProductiveUnitUpdateSchema())
def update_productive_unit(unit_id):
    item = _get_available_unit(unit_id)
    if not item:
        return error("Unidad Productiva no encontrada", 404)
    _update_fields(item, validated_json())
    try:
        audit("EDITAR", "ProductiveUnit", item.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("El correo o NIT ya está registrado", 409)
    invalidate_public_cache()
    return productive_unit_json(item)


@productive_unit_bp.patch("/admin/productive-units/<uuid:unit_id>/status")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
@validate_json(ProductiveUnitStatusSchema())
def update_productive_unit_status(unit_id):
    item = _get_available_unit(unit_id)
    if not item:
        return error("Unidad Productiva no encontrada", 404)
    item.estado = ProductiveUnitStatus(validated_json()["estado"])
    audit("CAMBIAR_ESTADO", "ProductiveUnit", item.id)
    db.session.commit()
    invalidate_public_cache()
    return productive_unit_json(item)


@productive_unit_bp.delete("/admin/productive-units/<uuid:unit_id>")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
def delete_productive_unit(unit_id):
    item = _get_available_unit(unit_id)
    if not item:
        return error("Unidad Productiva no encontrada", 404)
    item.deleted_at = datetime.now(timezone.utc)
    item.estado = ProductiveUnitStatus.INACTIVE
    user = db.session.get(User, item.user_id)
    user.deleted_at = item.deleted_at
    user.token_version += 1
    audit("ELIMINAR", "ProductiveUnit", item.id)
    db.session.commit()
    invalidate_public_cache()
    return {"message": "Unidad Productiva eliminada"}


@productive_unit_bp.post("/admin/productive-units/<uuid:unit_id>/restore")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
def restore_productive_unit(unit_id):
    item = db.session.get(ProductiveUnit, unit_id)
    if not item or not item.deleted_at:
        return error("Unidad Productiva eliminada no encontrada", 404)
    item.deleted_at = None
    item.estado = ProductiveUnitStatus.ACTIVE
    user = db.session.get(User, item.user_id)
    user.deleted_at = None
    audit("RESTAURAR", "ProductiveUnit", item.id)
    db.session.commit()
    invalidate_public_cache()
    return productive_unit_json(item)


@productive_unit_bp.get("/productive-unit/profile")
@roles(*ROLES_RESPONSABLES_UNIDAD)
def own_productive_unit_profile():
    item = current_productive_unit()
    return productive_unit_json(item) if item else error("Unidad Productiva no encontrada", 404)


@productive_unit_bp.patch("/productive-unit/profile")
@roles(*ROLES_RESPONSABLES_UNIDAD)
@validate_json(ProductiveUnitUpdateSchema())
def update_own_productive_unit_profile():
    item = current_productive_unit()
    if not item:
        return error("Unidad Productiva no encontrada", 404)
    if item.estado != ProductiveUnitStatus.ACTIVE:
        return error("La Unidad Productiva no permite modificaciones", 403)
    _update_fields(item, validated_json())
    try:
        audit("EDITAR", "ProductiveUnit", item.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("El correo o NIT ya está registrado", 409)
    invalidate_public_cache()
    return productive_unit_json(item)


@productive_unit_bp.get("/productive-unit/sectors")
@roles(*ROLES_RESPONSABLES_UNIDAD)
def own_unit_sectors():
    item = current_productive_unit()
    return {"sectores": productive_unit_json(item)["sectores"]} if item else error("Unidad Productiva no encontrada", 404)


@productive_unit_bp.put("/productive-unit/sectors")
@roles(*ROLES_RESPONSABLES_UNIDAD)
@validate_json(UnitSectorsSchema())
def replace_own_unit_sectors():
    item = current_productive_unit()
    if not item or item.estado != ProductiveUnitStatus.ACTIVE:
        return error("La Unidad Productiva no permite modificaciones", 403)
    try:
        rows = _validated_sector_rows(validated_json()["sectores"])
    except ValueError as exc:
        return error(str(exc))
    existing = {
        link.productive_sector_id: link
        for link in db.session.scalars(
            select(UnitSector).where(UnitSector.productive_unit_id == item.id)
        ).all()
    }
    before = [str(sector_id) for sector_id, link in existing.items() if link.estado == SectorStatus.ACTIVE]
    selected_ids = {sector.id for sector, _detail in rows}
    for sector_id, link in existing.items():
        if sector_id not in selected_ids:
            link.estado = SectorStatus.INACTIVE
    for sector, detail in rows:
        link = existing.get(sector.id)
        if link:
            link.estado = SectorStatus.ACTIVE
            link.detalle_otro = detail
        else:
            db.session.add(
                UnitSector(
                    productive_unit_id=item.id,
                    productive_sector_id=sector.id,
                    detalle_otro=detail,
                    estado=SectorStatus.ACTIVE,
                )
            )
    audit(
        "ASIGNAR_SECTORES",
        "ProductiveUnit",
        item.id,
        before={"sector_ids": before},
        after={"sector_ids": [str(sector_id) for sector_id in selected_ids]},
    )
    db.session.commit()
    invalidate_public_cache()
    return {"sectores": productive_unit_json(item)["sectores"]}


@productive_unit_bp.post("/productive-unit/logo")
@roles(*ROLES_RESPONSABLES_UNIDAD)
def upload_own_unit_logo():
    item = current_productive_unit()
    if not item or item.estado != ProductiveUnitStatus.ACTIVE:
        return error("La Unidad Productiva no permite modificaciones", 403)
    try:
        uploaded = upload_to_cloudinary(
            request.files.get("file"),
            "unidades_productivas",
            image_variant="unit_logo",
        )
    except ValueError as exc:
        return error(str(exc))
    if not uploaded:
        return error("La imagen es obligatoria")
    previous = item.logo_url
    previous_public_id = item.logo_public_id
    item.logo_url = uploaded["url"]
    item.logo_public_id = uploaded["public_id"]
    audit(
        "AGREGAR_IMAGEN",
        "ProductiveUnit",
        item.id,
        before={"logo_url": previous},
        after={"logo_url": item.logo_url},
    )
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        _delete_unit_logo(uploaded["url"], uploaded["public_id"])
        return error("No fue posible guardar el logotipo", 409)
    _delete_unit_logo(previous, previous_public_id)
    invalidate_public_cache()
    return {"logo_url": item.logo_url}, 201


@productive_unit_bp.delete("/productive-unit/logo")
@roles(*ROLES_RESPONSABLES_UNIDAD)
def delete_own_unit_logo():
    item = current_productive_unit()
    if not item:
        return error("Unidad Productiva no encontrada", 404)
    previous = item.logo_url
    previous_public_id = item.logo_public_id
    item.logo_url = None
    item.logo_public_id = None
    audit(
        "ELIMINAR_IMAGEN",
        "ProductiveUnit",
        item.id,
        before={"logo_url": previous},
        after={"logo_url": None},
    )
    db.session.commit()
    _delete_unit_logo(previous, previous_public_id)
    invalidate_public_cache()
    return {"message": "Logotipo eliminado"}
