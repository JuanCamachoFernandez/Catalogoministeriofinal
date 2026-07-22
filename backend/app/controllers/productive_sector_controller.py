from flask import Blueprint
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    ProductiveSector,
    RegistrationRequestSector,
    Role,
    SectorStatus,
    UnitSector,
)
from ..views import error, validate_json, validated_json
from ..views.domain_serializers import sector_json
from ..views.productive_sector_view import (
    ProductiveSectorSchema,
    ProductiveSectorStatusSchema,
    ProductiveSectorUpdateSchema,
)
from .common import audit, get_public_cache, invalidate_public_cache, roles, set_public_cache

productive_sector_bp = Blueprint("productive_sectors", __name__)
ADMIN_ROLES = (Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO, Role.ADMIN)


@productive_sector_bp.get("/productive-sectors")
def list_productive_sectors():
    key = ("canonical", "productive-sectors")
    cached = get_public_cache(key)
    if cached is not None:
        return cached
    items = db.session.scalars(ProductiveSector.active_query()).all()
    return set_public_cache(key, {"items": [sector_json(item) for item in items]})


@productive_sector_bp.post("/admin/productive-sectors")
@roles(*ADMIN_ROLES)
@validate_json(ProductiveSectorSchema())
def create_productive_sector():
    data = validated_json()
    name = data["nombre"].strip()
    if db.session.scalar(select(ProductiveSector.id).where(func.lower(ProductiveSector.nombre) == name.lower())):
        return error("El sector ya existe", 409)
    item = ProductiveSector(nombre=name, descripcion=data.get("descripcion"), es_otro=data.get("es_otro", False))
    if item.es_otro and db.session.scalar(select(ProductiveSector.id).where(ProductiveSector.es_otro.is_(True), ProductiveSector.deleted_at.is_(None))):
        return error("Ya existe un sector Otros", 409)
    db.session.add(item)
    audit("CREAR", "ProductiveSector", item.id)
    db.session.commit()
    invalidate_public_cache()
    return sector_json(item), 201


@productive_sector_bp.get("/admin/productive-sectors/<uuid:sector_id>")
@roles(*ADMIN_ROLES)
def get_productive_sector(sector_id):
    item = db.session.get(ProductiveSector, sector_id)
    return sector_json(item) if item and not item.deleted_at else error("Sector no encontrado", 404)


@productive_sector_bp.patch("/admin/productive-sectors/<uuid:sector_id>")
@roles(*ADMIN_ROLES)
@validate_json(ProductiveSectorUpdateSchema())
def update_productive_sector(sector_id):
    item = db.session.get(ProductiveSector, sector_id)
    if not item or item.deleted_at:
        return error("Sector no encontrado", 404)
    data = validated_json()
    if "nombre" in data:
        item.nombre = data["nombre"].strip()
    if "descripcion" in data:
        item.descripcion = data["descripcion"]
    if "es_otro" in data and data["es_otro"] != item.es_otro:
        if data["es_otro"] and db.session.scalar(select(ProductiveSector.id).where(ProductiveSector.es_otro.is_(True), ProductiveSector.id != item.id, ProductiveSector.deleted_at.is_(None))):
            return error("Ya existe un sector Otros", 409)
        if db.session.scalar(select(UnitSector.id).where(UnitSector.productive_sector_id == item.id)):
            return error("No se puede cambiar es_otro con asociaciones existentes", 409)
        item.es_otro = data["es_otro"]
    try:
        audit("EDITAR", "ProductiveSector", item.id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error("El nombre del sector ya existe", 409)
    invalidate_public_cache()
    return sector_json(item)


@productive_sector_bp.patch("/admin/productive-sectors/<uuid:sector_id>/status")
@roles(*ADMIN_ROLES)
@validate_json(ProductiveSectorStatusSchema())
def change_productive_sector_status(sector_id):
    item = db.session.get(ProductiveSector, sector_id)
    if not item or item.deleted_at:
        return error("Sector no encontrado", 404)
    item.estado = SectorStatus(validated_json()["estado"])
    audit("CAMBIAR_ESTADO", "ProductiveSector", item.id)
    db.session.commit()
    invalidate_public_cache()
    return sector_json(item)


@productive_sector_bp.delete("/admin/productive-sectors/<uuid:sector_id>")
@roles(*ADMIN_ROLES)
def delete_productive_sector(sector_id):
    item = db.session.get(ProductiveSector, sector_id)
    if not item or item.deleted_at:
        return error("Sector no encontrado", 404)
    associated = db.session.scalar(select(UnitSector.id).where(UnitSector.productive_sector_id == item.id)) or db.session.scalar(select(RegistrationRequestSector.id).where(RegistrationRequestSector.productive_sector_id == item.id))
    if associated:
        item.estado = SectorStatus.INACTIVE
        db.session.commit()
        invalidate_public_cache()
        return {"message": "Sector desactivado porque conserva asociaciones"}
    from datetime import datetime, timezone

    item.deleted_at = datetime.now(timezone.utc)
    item.estado = SectorStatus.INACTIVE
    audit("ELIMINAR", "ProductiveSector", item.id)
    db.session.commit()
    invalidate_public_cache()
    return {"message": "Sector eliminado"}
