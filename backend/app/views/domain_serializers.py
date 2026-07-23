from sqlalchemy import func, select

from ..extensions import db
from ..models import (
    Product,
    ProductImage,
    ProductiveSector,
    ProductiveUnit,
    RegistrationRequestSector,
    UnitSector,
)


def sector_json(item):
    return {
        "id": str(item.id),
        "nombre": item.nombre,
        "descripcion": item.descripcion,
        "estado": item.estado.value,
        "es_otro": item.es_otro,
        "fecha_creacion": item.created_at.isoformat(),
        "fecha_actualizacion": item.updated_at.isoformat(),
    }


def _sector_links(link_model, owner_field, owner_id):
    query = (
        select(link_model, ProductiveSector)
        .join(ProductiveSector, link_model.productive_sector_id == ProductiveSector.id)
        .where(getattr(link_model, owner_field) == owner_id)
        .order_by(ProductiveSector.nombre)
    )
    if hasattr(link_model, "estado"):
        from ..models import SectorStatus

        query = query.where(link_model.estado == SectorStatus.ACTIVE)
    rows = db.session.execute(query).all()
    return [
        {
            "id": str(sector.id),
            "nombre": sector.nombre,
            "estado": sector.estado.value,
            "es_otro": sector.es_otro,
            "detalle_otro": link.detalle_otro,
        }
        for link, sector in rows
    ]


def registration_request_json(item):
    return {
        "id": str(item.id),
        "nombre_comercial": item.nombre_comercial,
        "razon_social": item.razon_social,
        "nit": item.nit,
        "registro_seprec": item.registro_seprec,
        "registro_pro_bolivia": item.registro_pro_bolivia,
        "nombre_representante": item.nombre_representante,
        "nombres_representante": item.nombres_representante,
        "apellido_paterno_representante": item.apellido_paterno_representante,
        "apellido_materno_representante": item.apellido_materno_representante,
        "departamento": item.departamento,
        "direccion_fisica": item.direccion_fisica,
        "telefono_whatsapp": item.telefono_whatsapp,
        "correo_electronico": item.correo_electronico,
        "facebook_url": item.facebook_url,
        "instagram_url": item.instagram_url,
        "tiktok_url": item.tiktok_url,
        "resena_comercial": item.resena_comercial,
        "logo_url": item.logo_url,
        "estado": item.estado.value,
        "fecha_solicitud": item.created_at.isoformat(),
        "fecha_revision": item.fecha_revision.isoformat() if item.fecha_revision else None,
        "observaciones": item.observaciones,
        "motivo_rechazo": item.motivo_rechazo,
        "reviewed_by": str(item.reviewed_by) if item.reviewed_by else None,
        "credentials_sent_at": item.credentials_sent_at.isoformat() if item.credentials_sent_at else None,
        "notification_status": item.notification_status.value if item.notification_status else None,
        "fecha_actualizacion": item.updated_at.isoformat(),
        "sectores": _sector_links(
            RegistrationRequestSector, "registration_request_id", item.id
        ),
    }


def productive_unit_json(item, include_products=False):
    payload = {
        "id": str(item.id),
        "user_id": str(item.user_id),
        "registration_request_id": str(item.registration_request_id),
        "nombre_comercial": item.nombre_comercial,
        "razon_social": item.razon_social,
        "nit": item.nit,
        "registro_seprec": item.registro_seprec,
        "registro_pro_bolivia": item.registro_pro_bolivia,
        "nombre_representante": item.nombre_representante,
        "nombres_representante": item.nombres_representante,
        "apellido_paterno_representante": item.apellido_paterno_representante,
        "apellido_materno_representante": item.apellido_materno_representante,
        "departamento": item.departamento,
        "direccion_fisica": item.direccion_fisica,
        "telefono_whatsapp": item.telefono_whatsapp,
        "correo_electronico": item.correo_electronico,
        "facebook_url": item.facebook_url,
        "instagram_url": item.instagram_url,
        "tiktok_url": item.tiktok_url,
        "resena_comercial": item.resena_comercial,
        "logo_url": item.logo_url,
        "estado": item.estado.value,
        "fecha_aprobacion": item.fecha_aprobacion.isoformat(),
        "fecha_creacion": item.created_at.isoformat(),
        "fecha_actualizacion": item.updated_at.isoformat(),
        "sectores": _sector_links(UnitSector, "productive_unit_id", item.id),
    }
    if include_products:
        from .product_view import productive_product_json

        products = db.session.scalars(
            select(Product).where(
                Product.productive_unit_id == item.id, Product.deleted_at.is_(None)
            )
        ).all()
        payload["productos"] = [productive_product_json(product) for product in products]
    return payload
