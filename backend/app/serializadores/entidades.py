from sqlalchemy import select

from ..extensiones import db
from ..modelos import (
    Category,
    Exhibitor,
    ExhibitorType,
    ExhibitorTypeLink,
    ProductImage,
)


def user_json(user):
    profile_photo = user.foto_perfil
    if getattr(user, "exhibitor", None):
        exhibitor = db.session.scalar(
            select(Exhibitor).where(Exhibitor.user_id == user.id)
        )
        profile_photo = exhibitor.logo if exhibitor else None
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "foto_perfil": profile_photo,
        "must_change_password": user.must_change_password,
    }


def admin_user_json(user):
    profile = user.admin_profile
    return {
        **user_json(user),
        "apellido_paterno": user.apellido_paterno,
        "apellido_materno": user.apellido_materno,
        "phone": user.phone,
        "status": user.status.value,
        "cargo": profile.cargo if profile else None,
        "unidad": profile.unidad if profile else None,
        "observaciones": profile.observaciones if profile else None,
        "created_at": user.created_at.isoformat(),
    }


def fair_json(fair):
    return {
        "id": str(fair.id),
        "nombre": fair.nombre,
        "slug": fair.slug,
        "descripcion": fair.descripcion,
        "lugar": fair.lugar,
        "direccion": fair.direccion,
        "departamento": fair.departamento,
        "fecha_inicio": fair.fecha_inicio.isoformat(),
        "fecha_fin": fair.fecha_fin.isoformat(),
        "hora_inicio": fair.hora_inicio.isoformat() if fair.hora_inicio else None,
        "hora_fin": fair.hora_fin.isoformat() if fair.hora_fin else None,
        "fecha_limite_registro": (
            fair.fecha_limite_registro.isoformat()
            if fair.fecha_limite_registro
            else None
        ),
        "imagen_portada": fair.imagen_portada,
        "observaciones": fair.observaciones,
        "visible_publicamente": fair.visible_publicamente,
        "estado": fair.estado.value,
    }


def product_json(product):
    images = db.session.scalars(
        select(ProductImage)
        .where(ProductImage.product_id == product.id)
        .order_by(ProductImage.is_cover.desc(), ProductImage.display_order)
    ).all()
    category = db.session.get(Category, product.category_id)
    exhibitor = db.session.get(Exhibitor, product.exhibitor_id)
    return {
        "id": str(product.id),
        "exhibitor_id": str(product.exhibitor_id),
        "nombre_comercial": exhibitor.nombre_comercial if exhibitor else None,
        "category_id": str(product.category_id),
        "categoria": (
            {"id": str(category.id), "nombre": category.nombre}
            if category
            else None
        ),
        "nombre": product.nombre,
        "slug": product.slug,
        "descripcion": product.descripcion,
        "materiales_o_ingredientes": product.materiales_o_ingredientes,
        "lugar_origen": product.lugar_origen,
        "presentacion": product.presentacion,
        "informacion_adicional": product.informacion_adicional,
        "precio": float(product.precio) if product.precio is not None else None,
        "estado": product.estado.value,
        "destacado": product.destacado,
        "imagenes": [
            {
                "id": str(image.id),
                "url": image.url,
                "alt_text": image.alt_text,
                "is_cover": image.is_cover,
                "display_order": image.display_order,
            }
            for image in images
        ],
    }


def exhibitor_json(exhibitor):
    type_rows = db.session.execute(
        select(ExhibitorTypeLink, ExhibitorType)
        .join(ExhibitorType, ExhibitorTypeLink.type_id == ExhibitorType.id)
        .where(ExhibitorTypeLink.exhibitor_id == exhibitor.id)
        .order_by(ExhibitorType.nombre)
    ).all()
    return {
        "id": str(exhibitor.id),
        "user_id": str(exhibitor.user_id),
        "nombre_comercial": exhibitor.nombre_comercial,
        "tipo_documento": exhibitor.tipo_documento.value,
        "numero_documento": exhibitor.numero_documento,
        "nombre_responsable": exhibitor.nombre_responsable,
        "apellido_responsable": exhibitor.apellido_responsable,
        "apellido_paterno_responsable": exhibitor.apellido_paterno_responsable,
        "apellido_materno_responsable": exhibitor.apellido_materno_responsable,
        "telefono_whatsapp": exhibitor.telefono_whatsapp,
        "correo": exhibitor.correo,
        "departamento": exhibitor.departamento,
        "municipio": exhibitor.municipio,
        "direccion": exhibitor.direccion,
        "descripcion": exhibitor.descripcion,
        "descripcion_productos": exhibitor.descripcion_productos,
        "nombre_tipo_expositor": exhibitor.nombre_tipo_expositor,
        "type_ids": [str(link.type_id) for link, _ in type_rows],
        "tipos_expositor": [type_item.nombre for _, type_item in type_rows],
        "logo": exhibitor.logo,
        "estado": exhibitor.estado.value,
        "created_at": exhibitor.created_at.isoformat(),
    }


def assignment_json(assignment):
    exhibitor = db.session.get(Exhibitor, assignment.exhibitor_id)
    return {
        "id": str(assignment.id),
        "fair_id": str(assignment.fair_id),
        "exhibitor_id": str(assignment.exhibitor_id),
        "nombre_comercial": exhibitor.nombre_comercial if exhibitor else None,
        "estado": assignment.estado.value,
        "numero_stand": assignment.numero_stand,
        "sector": assignment.sector,
        "observaciones": assignment.observaciones,
        "authorized_by": (
            str(assignment.authorized_by) if assignment.authorized_by else None
        ),
        "authorized_at": (
            assignment.authorized_at.isoformat()
            if assignment.authorized_at
            else None
        ),
    }
