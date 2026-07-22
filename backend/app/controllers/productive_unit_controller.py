from datetime import datetime, timezone
from pathlib import Path
import shutil

from flask import Blueprint, current_app, request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    ProductiveSector,
    ProductiveUnit,
    ProductiveUnitStatus,
    Role,
    SectorStatus,
    UnitSector,
    User,
)
from ..views import error, paginate, validate_json, validated_json
from ..views.domain_serializers import productive_unit_json
from ..views.productive_unit_view import (
    ProductiveUnitStatusSchema,
    ProductiveUnitUpdateSchema,
    UnitSectorsSchema,
)
from .common import (
    audit,
    current_user,
    delete_managed_upload,
    invalidate_public_cache,
    roles,
    save_upload,
)
from .registration_controller import ADMIN_ROLES, _validated_sector_rows

productive_unit_bp = Blueprint("productive_units", __name__)
RESPONSIBLE_ROLES = (Role.PRODUCTIVE_UNIT_RESPONSIBLE, Role.EXPOSITOR)


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


def _update_fields(item, data, allow_email=True):
    allowed = {
        "nombre_comercial", "razon_social", "nit", "registro_seprec",
        "registro_pro_bolivia", "nombre_representante", "departamento",
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


@productive_unit_bp.get("/admin/productive-units")
@roles(*ADMIN_ROLES)
def list_productive_units():
    query = select(ProductiveUnit)
    if request.args.get("include_deleted") != "true":
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
    return paginate(query.order_by(ProductiveUnit.created_at.desc()), productive_unit_json)


@productive_unit_bp.get("/admin/productive-units/<uuid:unit_id>")
@roles(*ADMIN_ROLES)
def get_productive_unit(unit_id):
    item = db.session.get(ProductiveUnit, unit_id)
    return productive_unit_json(item) if item else error("Unidad Productiva no encontrada", 404)


@productive_unit_bp.patch("/admin/productive-units/<uuid:unit_id>")
@roles(*ADMIN_ROLES)
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
@roles(*ADMIN_ROLES)
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
@roles(*ADMIN_ROLES)
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
@roles(*ADMIN_ROLES)
def restore_productive_unit(unit_id):
    item = db.session.get(ProductiveUnit, unit_id)
    if not item or not item.deleted_at:
        return error("Unidad Productiva eliminada no encontrada", 404)
    item.deleted_at = None
    item.estado = ProductiveUnitStatus.INACTIVE
    user = db.session.get(User, item.user_id)
    user.deleted_at = None
    audit("RESTAURAR", "ProductiveUnit", item.id)
    db.session.commit()
    invalidate_public_cache()
    return productive_unit_json(item)


@productive_unit_bp.get("/productive-unit/profile")
@roles(*RESPONSIBLE_ROLES)
def own_productive_unit_profile():
    item = current_productive_unit()
    return productive_unit_json(item) if item else error("Unidad Productiva no encontrada", 404)


@productive_unit_bp.patch("/productive-unit/profile")
@roles(*RESPONSIBLE_ROLES)
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
@roles(*RESPONSIBLE_ROLES)
def own_unit_sectors():
    item = current_productive_unit()
    return {"sectores": productive_unit_json(item)["sectores"]} if item else error("Unidad Productiva no encontrada", 404)


@productive_unit_bp.put("/productive-unit/sectors")
@roles(*RESPONSIBLE_ROLES)
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
@roles(*RESPONSIBLE_ROLES)
def upload_own_unit_logo():
    item = current_productive_unit()
    if not item or item.estado != ProductiveUnitStatus.ACTIVE:
        return error("La Unidad Productiva no permite modificaciones", 403)
    try:
        new_url = save_upload(request.files.get("file"), "unidades_productivas")
    except ValueError as exc:
        return error(str(exc))
    if not new_url:
        return error("La imagen es obligatoria")
    previous = item.logo_url
    item.logo_url = new_url
    audit(
        "AGREGAR_IMAGEN",
        "ProductiveUnit",
        item.id,
        before={"logo_url": previous},
        after={"logo_url": new_url},
    )
    db.session.commit()
    delete_managed_upload(previous, "unidades_productivas")
    invalidate_public_cache()
    return {"logo_url": new_url}, 201


@productive_unit_bp.delete("/productive-unit/logo")
@roles(*RESPONSIBLE_ROLES)
def delete_own_unit_logo():
    item = current_productive_unit()
    if not item:
        return error("Unidad Productiva no encontrada", 404)
    previous = item.logo_url
    item.logo_url = None
    audit(
        "ELIMINAR_IMAGEN",
        "ProductiveUnit",
        item.id,
        before={"logo_url": previous},
        after={"logo_url": None},
    )
    db.session.commit()
    delete_managed_upload(previous, "unidades_productivas")
    invalidate_public_cache()
    return {"message": "Logotipo eliminado"}
