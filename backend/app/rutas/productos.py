from datetime import datetime, timezone
import os
import uuid

from flask import Blueprint, request
from sqlalchemy import func, select

from ..extensiones import db
from ..modelos import (
    Category,
    Exhibitor,
    Product,
    ProductImage,
    ProductStatus,
    ProductiveUnit,
    Role,
    ProductiveUnitStatus,
)
from ..esquemas import error, paginate, product_json, validate_json, validated_json
from ..esquemas.productos import (
    ProductCreateSchema,
    ProductImageUpdateSchema,
    ProductUpdateSchema,
    ProductImageOrderSchema,
    ProductiveProductCreateSchema,
    ProductiveProductStatusSchema,
    ProductiveProductUpdateSchema,
    productive_product_json,
)
from ..servicios import (
    audit,
    delete_managed_upload,
    invalidate_public_cache,
    product_from_payload,
    require_managed_upload,
    save_upload,
)

from ..autenticacion.decoradores import roles
from ..autenticacion.sesiones import current_user
from ..autenticacion.permisos import (
    ROLES_ADMINISTRACION_COMPLETA,
    ROLES_ADMINISTRACION_INSTITUCIONAL,
    ROLES_EXPOSITOR,
    ROLES_GESTION_COMPARTIDA_LEGADA,
    ROLES_RESPONSABLES_UNIDAD,
)
product_bp = Blueprint("products", __name__)
MAX_PRODUCTIVE_UNIT_PRODUCTS = 15


def productive_product_or_404(product_id, unit_id=None):
    product = db.session.get(Product, product_id)
    if not product or product.deleted_at or not product.productive_unit_id:
        return None
    if unit_id and product.productive_unit_id != unit_id:
        return None
    return product


def _productive_unit_for_write():
    from .unidades_productivas import current_productive_unit

    unit = current_productive_unit()
    return unit if unit and unit.estado == ProductiveUnitStatus.ACTIVE and not unit.deleted_at else None


def _productive_product_count(unit_id, excluding_id=None):
    query = select(func.count(Product.id)).where(
        Product.productive_unit_id == unit_id,
        Product.deleted_at.is_(None),
    )
    if excluding_id:
        query = query.where(Product.id != excluding_id)
    return db.session.scalar(query) or 0


def _set_productive_product_fields(product, data):
    for field in (
        "nombre_comercial", "descripcion_tecnica", "materia_prima", "dimensiones",
        "colores_disponibles", "certificaciones", "presentacion_empaque",
        "precio_referencia", "capacidad_produccion_stock",
    ):
        if field in data:
            value = data[field].strip() if isinstance(data[field], str) else data[field]
            setattr(product, field, value)
    # Keep legacy columns populated during the compatibility window.
    product.nombre = product.nombre_comercial
    product.descripcion = product.descripcion_tecnica
    product.materiales_o_ingredientes = product.materia_prima
    product.presentacion = product.presentacion_empaque
    product.precio = product.precio_referencia
    product.slug = __import__("app.utilidades", fromlist=["slugify"]).slugify(product.nombre_comercial)


def _image_count(product_id):
    return db.session.scalar(select(func.count(ProductImage.id)).where(ProductImage.product_id == product_id)) or 0


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
    if not existing_images:
        is_cover = True
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
@roles(*ROLES_ADMINISTRACION_INSTITUCIONAL)
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
    return paginate(query.order_by(Product.created_at.desc(), Product.id.desc()), product_json)


@product_bp.get("/products/<uuid:product_id>")
@roles(*ROLES_ADMINISTRACION_INSTITUCIONAL)
def get_admin_product(product_id):
    product = product_or_404(product_id)
    return product_json(product) if product else error("Producto no encontrado", 404)


@product_bp.post("/products")
@roles(*ROLES_ADMINISTRACION_INSTITUCIONAL)
@validate_json(ProductCreateSchema())
def create_admin_product():
    return error("Los productos solo pueden ser creados por su expositor", 403)


@product_bp.patch("/products/<uuid:product_id>")
@roles(*ROLES_ADMINISTRACION_INSTITUCIONAL)
@validate_json(ProductUpdateSchema())
def update_admin_product(product_id):
    return error("Los productos solo pueden ser editados por su expositor", 403)


@product_bp.delete("/products/<uuid:product_id>")
@roles(*ROLES_ADMINISTRACION_INSTITUCIONAL)
def delete_admin_product(product_id):
    return error("Los productos solo pueden ser eliminados por su expositor", 403)


@product_bp.get("/exhibitor/products")
@roles(*ROLES_EXPOSITOR)
def own_products():
    exhibitor = current_user().exhibitor
    query = Product.owned_query(exhibitor.id).order_by(Product.created_at.desc(), Product.id.desc())
    return paginate(query, product_json)


@product_bp.get("/exhibitor/products/<uuid:product_id>")
@roles(*ROLES_EXPOSITOR)
def get_own_product(product_id):
    product = product_or_404(product_id, current_user().exhibitor.id)
    return product_json(product) if product else error("Producto no encontrado", 404)


@product_bp.post("/exhibitor/products")
@roles(*ROLES_EXPOSITOR)
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
@roles(*ROLES_EXPOSITOR)
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
@roles(*ROLES_EXPOSITOR)
def delete_own_product(product_id):
    product = product_or_404(product_id, current_user().exhibitor.id)
    if not product:
        return error("Producto no encontrado", 404)
    delete_product_record(product)
    return "", 204


@product_bp.get("/products/<uuid:product_id>/images")
@roles(*ROLES_ADMINISTRACION_INSTITUCIONAL)
def list_admin_product_images(product_id):
    product = product_or_404(product_id)
    if not product:
        return error("Producto no encontrado", 404)
    return {"items": product_json(product)["imagenes"]}


@product_bp.post("/products/<uuid:product_id>/images")
@roles(*ROLES_ADMINISTRACION_INSTITUCIONAL)
def add_admin_product_image(product_id):
    return error("Las imágenes solo pueden ser gestionadas por su expositor", 403)


@product_bp.post("/exhibitor/products/<uuid:product_id>/images")
@roles(*ROLES_EXPOSITOR)
def add_own_product_image(product_id):
    product = product_or_404(product_id, current_user().exhibitor.id)
    return add_product_image(product) if product else error("Producto no encontrado", 404)


@product_bp.patch("/product-images/<uuid:image_id>")
@roles(*ROLES_GESTION_COMPARTIDA_LEGADA)
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
@roles(*ROLES_GESTION_COMPARTIDA_LEGADA)
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


# Canonical productive-unit API.  Legacy exhibitor routes above remain as aliases
# until the frontend migration is completed.
@product_bp.get("/productive-unit/products")
@roles(*ROLES_RESPONSABLES_UNIDAD)
def own_productive_products():
    from .unidades_productivas import current_productive_unit

    unit = current_productive_unit()
    if not unit:
        return error("Unidad Productiva no encontrada", 404)
    query = select(Product).where(
        Product.productive_unit_id == unit.id, Product.deleted_at.is_(None)
    ).order_by(Product.created_at.desc(), Product.id.desc())
    return paginate(query, productive_product_json)


@product_bp.get("/productive-unit/products/<uuid:product_id>")
@roles(*ROLES_RESPONSABLES_UNIDAD)
def get_own_productive_product(product_id):
    from .unidades_productivas import current_productive_unit

    unit = current_productive_unit()
    product = productive_product_or_404(product_id, unit.id if unit else None)
    return productive_product_json(product) if product else error("Producto no encontrado", 404)


@product_bp.post("/productive-unit/products")
@roles(*ROLES_RESPONSABLES_UNIDAD)
@validate_json(ProductiveProductCreateSchema())
def create_productive_product():
    unit = _productive_unit_for_write()
    if not unit:
        return error("La Unidad Productiva no permite modificaciones", 403)
    # Serialize creations for the same unit so concurrent requests cannot
    # exceed the configured quota.
    db.session.scalar(
        select(ProductiveUnit).where(ProductiveUnit.id == unit.id).with_for_update()
    )
    if _productive_product_count(unit.id) >= MAX_PRODUCTIVE_UNIT_PRODUCTS:
        return error(
            f"La Unidad Productiva puede registrar como máximo {MAX_PRODUCTIVE_UNIT_PRODUCTS} productos",
            409,
        )
    product = Product(productive_unit_id=unit.id, estado=ProductStatus.DRAFT)
    _set_productive_product_fields(product, validated_json())
    db.session.add(product)
    db.session.flush()
    audit("CREAR", "Product", product.id)
    db.session.commit()
    invalidate_public_cache()
    return productive_product_json(product), 201


@product_bp.patch("/productive-unit/products/<uuid:product_id>")
@roles(*ROLES_RESPONSABLES_UNIDAD)
@validate_json(ProductiveProductUpdateSchema())
def update_productive_product(product_id):
    unit = _productive_unit_for_write()
    product = productive_product_or_404(product_id, unit.id if unit else None)
    if not product:
        return error("Producto no encontrado", 404)
    _set_productive_product_fields(product, validated_json())
    audit("EDITAR", "Product", product.id)
    db.session.commit()
    invalidate_public_cache()
    return productive_product_json(product)


@product_bp.patch("/productive-unit/products/<uuid:product_id>/status")
@roles(*ROLES_RESPONSABLES_UNIDAD)
@validate_json(ProductiveProductStatusSchema())
def update_productive_product_status(product_id):
    unit = _productive_unit_for_write()
    product = productive_product_or_404(product_id, unit.id if unit else None)
    if not product:
        return error("Producto no encontrado", 404)
    status = ProductStatus(validated_json()["estado"])
    if status in (ProductStatus.AVAILABLE, ProductStatus.OUT_OF_STOCK) and _image_count(product.id) != 3:
        return error("El producto necesita exactamente tres imágenes para publicarse", 409)
    product.estado = status
    audit("CAMBIAR_ESTADO", "Product", product.id)
    db.session.commit()
    invalidate_public_cache()
    return productive_product_json(product)


@product_bp.delete("/productive-unit/products/<uuid:product_id>")
@roles(*ROLES_RESPONSABLES_UNIDAD)
def delete_productive_product(product_id):
    unit = _productive_unit_for_write()
    product = productive_product_or_404(product_id, unit.id if unit else None)
    if not product:
        return error("Producto no encontrado", 404)
    # Keep the managed file paths until the permanent database deletion commits.
    urls = db.session.scalars(select(ProductImage.url).where(ProductImage.product_id == product.id)).all()
    db.session.execute(db.delete(ProductImage).where(ProductImage.product_id == product.id))
    audit(
        "ELIMINAR_PERMANENTE",
        "Product",
        product.id,
        before={"nombre_comercial": product.nombre_comercial, "estado": product.estado.value},
    )
    db.session.delete(product)
    db.session.commit()
    for url in urls:
        delete_managed_upload(url, "productos")
    invalidate_public_cache()
    return "", 204


@product_bp.get("/admin/products")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
def list_admin_productive_products():
    query = select(Product).where(Product.productive_unit_id.is_not(None))
    if request.args.get("q"):
        term = request.args["q"].strip()
        query = query.where(Product.nombre_comercial.ilike(f"%{term}%"))
    if request.args.get("productive_unit_id"):
        query = query.where(Product.productive_unit_id == request.args["productive_unit_id"])
    if request.args.get("estado"):
        try:
            query = query.where(Product.estado == ProductStatus(request.args["estado"]))
        except ValueError:
            return error("Estado inválido")
    return paginate(
        query.order_by(Product.created_at.desc(), Product.id.desc()),
        productive_product_json,
    )


@product_bp.get("/admin/products/<uuid:product_id>")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
def get_admin_productive_product(product_id):
    product = productive_product_or_404(product_id)
    return productive_product_json(product) if product else error("Producto no encontrado", 404)


@product_bp.patch("/admin/products/<uuid:product_id>/status")
@roles(*ROLES_ADMINISTRACION_COMPLETA)
@validate_json(ProductiveProductStatusSchema())
def admin_productive_product_status(product_id):
    product = productive_product_or_404(product_id)
    if not product:
        return error("Producto no encontrado", 404)
    status = ProductStatus(validated_json()["estado"])
    if status in (ProductStatus.AVAILABLE, ProductStatus.OUT_OF_STOCK) and _image_count(product.id) != 3:
        return error("El producto necesita exactamente tres imágenes para publicarse", 409)
    product.estado = status
    audit("CAMBIAR_ESTADO", "Product", product.id)
    db.session.commit()
    invalidate_public_cache()
    return productive_product_json(product)


def _own_product_image_context(product_id, image_id=None):
    unit = _productive_unit_for_write()
    product = productive_product_or_404(product_id, unit.id if unit else None)
    image = db.session.get(ProductImage, image_id) if image_id else None
    if image_id and (not image or not product or image.product_id != product.id):
        image = None
    return product, image


@product_bp.get("/productive-unit/products/<uuid:product_id>/images")
@roles(*ROLES_RESPONSABLES_UNIDAD)
def list_own_productive_product_images(product_id):
    from .unidades_productivas import current_productive_unit

    unit = current_productive_unit()
    product = productive_product_or_404(product_id, unit.id if unit else None)
    return {"items": productive_product_json(product)["imagenes"]} if product else error("Producto no encontrado", 404)


@product_bp.post("/productive-unit/products/<uuid:product_id>/images")
@roles(*ROLES_RESPONSABLES_UNIDAD)
def add_own_productive_product_image(product_id):
    product, _ = _own_product_image_context(product_id)
    if not product:
        return error("Producto no encontrado", 404)
    product = db.session.scalar(select(Product).where(Product.id == product.id).with_for_update())
    if _image_count(product.id) >= 3:
        return error("Un producto admite como máximo tres imágenes", 409)
    result = add_product_image(product)
    return result


@product_bp.patch("/productive-unit/products/<uuid:product_id>/images/<uuid:image_id>")
@roles(*ROLES_RESPONSABLES_UNIDAD)
@validate_json(ProductImageUpdateSchema())
def update_own_productive_product_image(product_id, image_id):
    product, image = _own_product_image_context(product_id, image_id)
    if not image:
        return error("Imagen no encontrada", 404)
    data = validated_json()
    previous_url = None
    if request.files.get("file"):
        try:
            new_url = save_upload(request.files["file"], "productos")
        except ValueError as exc:
            return error(str(exc))
        previous_url = image.url
        image.url = new_url
        image.filename = os.path.basename(new_url)
    if "alt_text" in data:
        image.alt_text = data["alt_text"]
    if "display_order" in data:
        if data["display_order"] >= _image_count(product.id):
            return error("Orden inválido")
        other = db.session.scalar(
            select(ProductImage).where(
                ProductImage.product_id == product.id,
                ProductImage.display_order == data["display_order"],
                ProductImage.id != image.id,
            )
        )
        if other:
            other.display_order = image.display_order
        image.display_order = data["display_order"]
    audit(
        "EDITAR_IMAGEN",
        "Product",
        product.id,
        after={"image_id": str(image.id), "display_order": image.display_order},
    )
    db.session.commit()
    if previous_url:
        delete_managed_upload(previous_url, "productos")
    invalidate_public_cache()
    return productive_product_json(product)


@product_bp.delete("/productive-unit/products/<uuid:product_id>/images/<uuid:image_id>")
@roles(*ROLES_RESPONSABLES_UNIDAD)
def delete_own_productive_product_image(product_id, image_id):
    product, image = _own_product_image_context(product_id, image_id)
    if not image:
        return error("Imagen no encontrada", 404)
    if product.estado in (ProductStatus.AVAILABLE, ProductStatus.OUT_OF_STOCK):
        product.estado = ProductStatus.DRAFT
    url = image.url
    db.session.delete(image)
    db.session.flush()
    remaining = db.session.scalars(select(ProductImage).where(ProductImage.product_id == product.id).order_by(ProductImage.display_order)).all()
    for order, item in enumerate(remaining):
        item.display_order = order
    if remaining and not any(item.is_cover for item in remaining):
        remaining[0].is_cover = True
    audit(
        "ELIMINAR_IMAGEN",
        "Product",
        product.id,
        before={"image_id": str(image.id), "url": url},
    )
    db.session.commit()
    delete_managed_upload(url, "productos")
    invalidate_public_cache()
    return "", 204


@product_bp.patch("/productive-unit/products/<uuid:product_id>/images/<uuid:image_id>/main")
@roles(*ROLES_RESPONSABLES_UNIDAD)
def set_own_productive_product_main_image(product_id, image_id):
    product, image = _own_product_image_context(product_id, image_id)
    if not image:
        return error("Imagen no encontrada", 404)
    for item in db.session.scalars(select(ProductImage).where(ProductImage.product_id == product.id)).all():
        item.is_cover = item.id == image.id
    audit(
        "EDITAR_IMAGEN",
        "Product",
        product.id,
        after={"main_image_id": str(image.id)},
    )
    db.session.commit()
    invalidate_public_cache()
    return productive_product_json(product)


@product_bp.patch("/productive-unit/products/<uuid:product_id>/images/order")
@roles(*ROLES_RESPONSABLES_UNIDAD)
@validate_json(ProductImageOrderSchema())
def reorder_own_productive_product_images(product_id):
    product, _ = _own_product_image_context(product_id)
    if not product:
        return error("Producto no encontrado", 404)
    image_ids = validated_json()["image_ids"]
    images = db.session.scalars(select(ProductImage).where(ProductImage.product_id == product.id)).all()
    if len(image_ids) != len(images) or set(image_ids) != {item.id for item in images}:
        return error("Debe incluir todas las imágenes una sola vez")
    mapping = {item.id: item for item in images}
    for order, image_id in enumerate(image_ids):
        mapping[image_id].display_order = order
    audit(
        "EDITAR_IMAGEN",
        "Product",
        product.id,
        after={"image_ids": [str(image_id) for image_id in image_ids]},
    )
    db.session.commit()
    invalidate_public_cache()
    return productive_product_json(product)
