from decimal import Decimal, InvalidOperation
import uuid

from ..modelos import ProductStatus
from ..utilidades import slugify


def parse_money(value):
    if value in (None, ""):
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("El precio debe ser numérico") from exc
    if amount < 0:
        raise ValueError("El precio no puede ser negativo")
    return amount.quantize(Decimal("0.01"))


def product_from_payload(product, data, exhibitor_id=None):
    if exhibitor_id:
        product.exhibitor_id = exhibitor_id
    if "category_id" in data:
        try:
            value = data.get("category_id")
            product.category_id = value if isinstance(value, uuid.UUID) else uuid.UUID(value or "")
        except (ValueError, TypeError) as exc:
            raise ValueError("Categoría inválida") from exc
    if "nombre" in data:
        name = (data.get("nombre") or "").strip()
        if not name:
            raise ValueError("El nombre del producto es obligatorio")
        product.nombre = name
        product.slug = slugify(name)
    if "descripcion" in data:
        product.descripcion = data.get("descripcion") or ""
    if "precio" in data:
        product.precio = parse_money(data.get("precio"))
    for field in ("materiales_o_ingredientes", "lugar_origen", "presentacion", "informacion_adicional"):
        if field in data:
            setattr(product, field, data.get(field))
    if "estado" in data:
        try:
            product.estado = ProductStatus(data.get("estado"))
        except ValueError as exc:
            raise ValueError("Estado de producto inválido") from exc
    if "destacado" in data:
        product.destacado = bool(data.get("destacado"))
    return product
