from datetime import datetime, timezone
import os
import uuid

from flask import Blueprint, request
from sqlalchemy import func, select

from ..extensions import db
from ..models import (
    Category,
    Exhibitor,
    Product,
    ProductImage,
    ProductStatus,
    Role,
)
from ..views import error, paginate, product_json, validate_json, validated_json
from ..views.product_view import (
    ProductCreateSchema,
    ProductImageUpdateSchema,
    ProductUpdateSchema,
)
from .common import (
    audit,
    current_user,
    delete_managed_upload,
    invalidate_public_cache,
    product_from_payload,
    require_managed_upload,
    roles,
    save_upload,
)

product_bp = Blueprint("products", __name__)


def product_or_404(product_id, exhibitor_id=None):
    product = db.session.get(Product, product_id)
    if (
        not product
        or product.deleted_at
        or (exhibitor_id and product.exhibitor_id != exhibitor_id)
    ):
        return None
    return product


def validate_product_references(product):
    category = db.session.get(Category, product.category_id)
    if not category or category.deleted_at or not category.estado:
        raise ValueError("Categoría no disponible")


def add_product_image(product):
    payload = request.get_json(silent=True) or {}
    alt_text = (request.form.get("alt_text") or payload.get("alt_text") or "").strip()
    if not alt_text:
        return error("El texto alternativo es obligatorio")
    existing_images = db.session.scalars(
        select(ProductImage)
        .where(ProductImage.product_id == product.id)
        .order_by(ProductImage.display_order, ProductImage.created_at, ProductImage.id)
    ).all()
    display_order = len(existing_images)
    try:
        url = save_upload(request.files.get("file"), "productos")
        if not url:
            url = payload.get("url")
            require_managed_upload(url, "productos")
    except ValueError as exc:
        return error(str(exc))
    is_cover_value = request.form.get("is_cover")
    is_cover = (
        str(is_cover_value).lower() in ("1", "true", "yes")
        if is_cover_value is not None
        else bool(payload.get("is_cover"))
    )
    image = ProductImage(
        product_id=product.id,
        filename=os.path.basename(url),
        url=url,
        alt_text=alt_text,
        is_cover=is_cover,
        display_order=display_order,
    )
    if image.is_cover:
        for other in existing_images:
            other.is_cover = False
    db.session.add(image)
    audit("AGREGAR_IMAGEN", "Producto", product.id, "Imagen agregada")
    db.session.commit()
    invalidate_public_cache()
    return {
        "id": str(image.id),
        "url": image.url,
        "is_cover": image.is_cover,
        "display_order": image.display_order,
    }, 201


def delete_product_record(product):
    images = db.session.scalars(
        select(ProductImage).where(ProductImage.product_id == product.id)
    ).all()
    urls = [image.url for image in images]
    for image in images:
        db.session.delete(image)
    product.deleted_at = datetime.now(timezone.utc)
    product.estado = ProductStatus.DELETED
    audit("ELIMINAR", "Producto", product.id, "Eliminación lógica")
    db.session.commit()
    for url in urls:
        delete_managed_upload(url, "productos")
    invalidate_public_cache()


@product_bp.get("/products")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def list_products():
    exhibitor_id = None
    if request.args.get("exhibitor_id"):
        try:
            exhibitor_id = uuid.UUID(request.args["exhibitor_id"])
        except ValueError:
            return error("Expositor inválido")
    term = request.args.get("q", "").strip()
    query = Product.admin_query(exhibitor_id, term)
    if request.args.get("category_id"):
        try:
            category_id = uuid.UUID(request.args["category_id"])
        except ValueError:
            return error("Categoría inválida")
        query = query.where(Product.category_id == category_id)
    if request.args.get("estado") in {item.value for item in ProductStatus}:
        query = query.where(Product.estado == ProductStatus(request.args["estado"]))
    if request.args.get("destacado") in {"true", "false"}:
        query = query.where(Product.destacado.is_(request.args["destacado"] == "true"))
    if request.args.get("date_from"):
        query = query.where(func.date(Product.created_at) >= request.args["date_from"])
    if request.args.get("date_to"):
        query = query.where(func.date(Product.created_at) <= request.args["date_to"])
    return paginate(query.order_by(Product.created_at.desc()), product_json)


@product_bp.get("/products/<uuid:product_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def get_admin_product(product_id):
    product = product_or_404(product_id)
    return product_json(product) if product else error("Producto no encontrado", 404)


@product_bp.post("/products")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(ProductCreateSchema())
def create_admin_product():
    return error("Los productos solo pueden ser creados por su expositor", 403)


@product_bp.patch("/products/<uuid:product_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(ProductUpdateSchema())
def update_admin_product(product_id):
    return error("Los productos solo pueden ser editados por su expositor", 403)


@product_bp.delete("/products/<uuid:product_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def delete_admin_product(product_id):
    return error("Los productos solo pueden ser eliminados por su expositor", 403)


@product_bp.get("/exhibitor/products")
@roles(Role.EXPOSITOR)
def own_products():
    exhibitor = current_user().exhibitor
    query = Product.owned_query(exhibitor.id).order_by(Product.created_at.desc())
    return paginate(query, product_json)


@product_bp.get("/exhibitor/products/<uuid:product_id>")
@roles(Role.EXPOSITOR)
def get_own_product(product_id):
    product = product_or_404(product_id, current_user().exhibitor.id)
    return product_json(product) if product else error("Producto no encontrado", 404)


@product_bp.post("/exhibitor/products")
@roles(Role.EXPOSITOR)
@validate_json(ProductCreateSchema())
def create_product():
    exhibitor = current_user().exhibitor
    data = validated_json()
    try:
        product = product_from_payload(
            Product(estado=ProductStatus.AVAILABLE), data, exhibitor.id
        )
        validate_product_references(product)
    except ValueError as exc:
        return error(str(exc))
    if not product.category_id or not product.descripcion:
        return error("Categoría y descripción son obligatorias")
    db.session.add(product)
    db.session.flush()
    audit("CREAR", "Producto", product.id, "Producto creado por expositor")
    db.session.commit()
    invalidate_public_cache()
    return product_json(product), 201


@product_bp.patch("/exhibitor/products/<uuid:product_id>")
@roles(Role.EXPOSITOR)
@validate_json(ProductUpdateSchema())
def update_own_product(product_id):
    product = product_or_404(product_id, current_user().exhibitor.id)
    if not product:
        return error("Producto no encontrado", 404)
    try:
        product_from_payload(product, validated_json())
        validate_product_references(product)
    except ValueError as exc:
        return error(str(exc))
    audit("EDITAR", "Producto", product.id, "Producto actualizado por expositor")
    db.session.commit()
    invalidate_public_cache()
    return product_json(product)


@product_bp.delete("/exhibitor/products/<uuid:product_id>")
@roles(Role.EXPOSITOR)
def delete_own_product(product_id):
    product = product_or_404(product_id, current_user().exhibitor.id)
    if not product:
        return error("Producto no encontrado", 404)
    delete_product_record(product)
    return "", 204


@product_bp.get("/products/<uuid:product_id>/images")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def list_admin_product_images(product_id):
    product = product_or_404(product_id)
    if not product:
        return error("Producto no encontrado", 404)
    return {"items": product_json(product)["imagenes"]}


@product_bp.post("/products/<uuid:product_id>/images")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def add_admin_product_image(product_id):
    return error("Las imágenes solo pueden ser gestionadas por su expositor", 403)


@product_bp.post("/exhibitor/products/<uuid:product_id>/images")
@roles(Role.EXPOSITOR)
def add_own_product_image(product_id):
    product = product_or_404(product_id, current_user().exhibitor.id)
    return add_product_image(product) if product else error("Producto no encontrado", 404)


@product_bp.patch("/product-images/<uuid:image_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO, Role.EXPOSITOR)
@validate_json(ProductImageUpdateSchema())
def update_product_image(image_id):
    user = current_user()
    if user.role != Role.EXPOSITOR:
        return error("Las imágenes solo pueden ser editadas por su expositor", 403)
    image = db.session.get(ProductImage, image_id)
    if not image:
        return error("Imagen no encontrada", 404)
    product = product_or_404(image.product_id)
    if product.exhibitor_id != user.exhibitor.id:
        return error("No autorizado", 403)
    data = validated_json()
    if data.get("is_cover"):
        for other in db.session.scalars(
            select(ProductImage).where(ProductImage.product_id == product.id)
        ).all():
            other.is_cover = other.id == image.id
    if "alt_text" in data:
        image.alt_text = data.get("alt_text")
    if "display_order" in data:
        try:
            image.display_order = int(data.get("display_order"))
        except (TypeError, ValueError):
            return error("Orden inválido")
    audit("EDITAR_IMAGEN", "Producto", product.id, f"Imagen actualizada del producto {product.nombre}")
    db.session.commit()
    invalidate_public_cache()
    return product_json(product)


@product_bp.delete("/product-images/<uuid:image_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO, Role.EXPOSITOR)
def delete_product_image(image_id):
    user = current_user()
    if user.role != Role.EXPOSITOR:
        return error("Las imágenes solo pueden ser eliminadas por su expositor", 403)
    image = db.session.get(ProductImage, image_id)
    if not image:
        return error("Imagen no encontrada", 404)
    product = product_or_404(image.product_id)
    if product.exhibitor_id != user.exhibitor.id:
        return error("No autorizado", 403)
    url = image.url
    db.session.delete(image)
    db.session.flush()
    remaining_images = db.session.scalars(
        select(ProductImage)
        .where(ProductImage.product_id == product.id)
        .order_by(ProductImage.display_order, ProductImage.created_at, ProductImage.id)
    ).all()
    for display_order, remaining in enumerate(remaining_images):
        remaining.display_order = display_order
    if remaining_images and not any(remaining.is_cover for remaining in remaining_images):
        remaining_images[0].is_cover = True
    audit("ELIMINAR_IMAGEN", "Producto", product.id, f"Imagen eliminada del producto {product.nombre}")
    db.session.commit()
    delete_managed_upload(url, "productos")
    invalidate_public_cache()
    return "", 204
