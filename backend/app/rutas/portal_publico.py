from urllib.parse import quote
import uuid

from flask import Blueprint, request
from sqlalchemy import select

from ..extensiones import db
from ..modelos import (
    AssignmentStatus,
    Exhibitor,
    Fair,
    FairExhibitor,
    FeriaStatus,
    Product,
    ProductStatus,
    UserStatus,
)
from ..utilidades import normalize_whatsapp
from ..esquemas import error, fair_json, paginate, product_json, validate_json, validated_json
from ..esquemas.productos import WhatsAppSchema
from .ferias import sync_fair_lifecycle
from ..servicios import get_public_cache, set_public_cache

public_bp = Blueprint("public", __name__)


def public_exhibitor_rows(fair_id):
    query = FairExhibitor.public_exhibitors_query(
        fair_id,
        request.args.get("q", "").strip(),
        request.args.get("departamento"),
    )
    return db.session.execute(query.order_by(Exhibitor.nombre_comercial)).all()


def public_fair_payload(fair):
    rows = public_exhibitor_rows(fair.id)
    return {
        **fair_json(fair),
        "expositores": [
            {
                "id": str(exhibitor.id),
                "nombre_comercial": exhibitor.nombre_comercial,
                "descripcion": exhibitor.descripcion,
                "logo": exhibitor.logo,
                "numero_stand": assignment.numero_stand,
                "sector": assignment.sector,
            }
            for exhibitor, assignment in rows
        ],
    }


@public_bp.get("/public/fairs")
def public_fairs():
    sync_fair_lifecycle()
    cache_key = ("public_fairs", tuple(sorted(request.args.items())))
    if cached := get_public_cache(cache_key):
        return cached
    query = Fair.active_query()
    term = request.args.get("q")
    if term:
        query = query.where(Fair.nombre.ilike(f"%{term}%"))
    if request.args.get("departamento"):
        query = query.where(Fair.departamento == request.args["departamento"])
    payload = paginate(query.order_by(Fair.fecha_inicio.desc()), fair_json)
    return set_public_cache(cache_key, payload)


@public_bp.get("/public/active-fair")
def public_active_fair():
    sync_fair_lifecycle()
    cache_key = ("active_fair", tuple(sorted(request.args.items())))
    if cached := get_public_cache(cache_key):
        return cached
    fair = db.session.scalar(Fair.active_query().order_by(Fair.fecha_inicio.desc()))
    if not fair:
        return error("No existe una feria activa", 404)
    return set_public_cache(cache_key, public_fair_payload(fair))


@public_bp.get("/public/fairs/<slug>")
def public_fair(slug):
    sync_fair_lifecycle()
    cache_key = ("fair", slug, tuple(sorted(request.args.items())))
    if cached := get_public_cache(cache_key):
        return cached
    fair = db.session.scalar(Fair.active_query().where(Fair.slug == slug))
    if not fair:
        return error("Feria no encontrada", 404)
    return set_public_cache(cache_key, public_fair_payload(fair))


@public_bp.get("/public/fairs/<slug>/exhibitors/<uuid:exhibitor_id>")
def public_exhibitor(slug, exhibitor_id):
    sync_fair_lifecycle()
    cache_key = (
        "public_exhibitor",
        slug,
        str(exhibitor_id),
        tuple(sorted(request.args.items())),
    )
    if cached := get_public_cache(cache_key):
        return cached
    row = db.session.execute(
        FairExhibitor.public_exhibitor_query(slug, exhibitor_id)
    ).first()
    if not row:
        return error("Expositor no disponible en esta feria", 404)
    _, exhibitor = row
    term = request.args.get("q", "").strip()
    category_id = None
    if request.args.get("category_id"):
        try:
            category_id = uuid.UUID(request.args["category_id"])
        except ValueError:
            return error("Categoría inválida")
    state = None
    if request.args.get("availability"):
        try:
            state = ProductStatus(request.args["availability"])
        except ValueError:
            return error("Disponibilidad inválida")
        if state not in (ProductStatus.AVAILABLE, ProductStatus.OUT_OF_STOCK):
            return error("Disponibilidad inválida")
    query = Product.public_query(exhibitor.id, term, category_id, state)
    paginated = paginate(query.order_by(Product.nombre), product_json)
    payload = {
        "id": str(exhibitor.id),
        "nombre_comercial": exhibitor.nombre_comercial,
        "descripcion": exhibitor.descripcion,
        "productos": paginated["items"],
        "pagination": paginated["pagination"],
    }
    return set_public_cache(cache_key, payload)


@public_bp.post("/public/whatsapp-query")
@validate_json(WhatsAppSchema())
def whatsapp_query():
    sync_fair_lifecycle()
    data = validated_json()
    raw_items = data.get("items")
    if raw_items is None:
        raw_items = [
            {"product_id": product_id, "quantity": 1}
            for product_id in data.get("product_ids") or []
        ]
    if not raw_items:
        return error("Seleccione al menos un producto")
    quantities = {}
    try:
        for item in raw_items:
            value = item.get("product_id")
            product_id = value if isinstance(value, uuid.UUID) else uuid.UUID(value or "")
            quantity = int(item.get("quantity", 1))
            if quantity <= 0:
                raise ValueError
            quantities[product_id] = quantities.get(product_id, 0) + quantity
    except (ValueError, TypeError, AttributeError):
        return error("Productos o cantidades inválidos")
    products = db.session.scalars(
        Product.available_by_ids_query(quantities)
    ).all()
    if len(products) != len(quantities):
        return error("Algún producto no está disponible")
    owners = {product.exhibitor_id for product in products}
    if len(owners) != 1:
        return error("La consulta solo puede contener productos de un mismo expositor")
    owner_id = owners.pop()
    exhibitor = db.session.get(Exhibitor, owner_id)
    assignment = db.session.scalar(
        FairExhibitor.authorized_query(data.get("fair_slug"), owner_id)
    )
    if (
        not assignment
        or not exhibitor
        or exhibitor.estado != UserStatus.ACTIVE
        or exhibitor.deleted_at
    ):
        return error("El expositor no está autorizado en esta feria", 403)
    phone = normalize_whatsapp(exhibitor.telefono_whatsapp)
    lines = "\n".join(
        f"• {product.nombre} — Cantidad: {quantities[product.id]}"
        for product in products
    )
    message = (
        "Hola, vi sus productos en Ferias Productivas Bolivia.\n\n"
        "Quisiera más información sobre los siguientes productos:\n"
        f"{lines}\n\nGracias."
    )
    return {"url": f"https://wa.me/{phone}?text={quote(message)}"}


# Canonical public catalogue based on FairParticipation -> ProductiveUnit -> Product.
def _active_canonical_fair():
    from .ferias import sync_fair_lifecycle
    from ..modelos import Fair

    sync_fair_lifecycle()
    return db.session.scalar(Fair.active_query().order_by(Fair.fecha_inicio.desc()))


def _active_canonical_fairs():
    from ..modelos import Fair

    sync_fair_lifecycle()
    return db.session.scalars(
        Fair.active_query().order_by(Fair.fecha_inicio.asc(), Fair.nombre.asc())
    ).all()


def _requested_canonical_fair():
    fair_id = request.args.get("fair_id")
    if not fair_id:
        return _active_canonical_fair()
    try:
        identifier = uuid.UUID(fair_id)
    except (TypeError, ValueError):
        return None
    return db.session.scalar(Fair.active_query().where(Fair.id == identifier))


def _canonical_fair_payload(fair):
    return {
        "id": str(fair.id), "nombre": fair.nombre, "descripcion": fair.descripcion,
        "ubicacion": fair.ubicacion or fair.lugar,
        "fecha_inicio": fair.fecha_inicio.isoformat(), "fecha_fin": fair.fecha_fin.isoformat(),
        "imagen_portada": fair.imagen_portada, "estado": fair.estado.value,
    }


def _visible_canonical_units(fair):
    from ..modelos import AssignmentStatus, FairParticipation, Product, ProductiveUnit, ProductiveUnitStatus

    rows = db.session.execute(
        select(ProductiveUnit, FairParticipation)
        .join(FairParticipation, FairParticipation.productive_unit_id == ProductiveUnit.id)
        .where(
            FairParticipation.fair_id == fair.id,
            FairParticipation.estado == AssignmentStatus.AUTHORIZED,
            ProductiveUnit.estado == ProductiveUnitStatus.ACTIVE,
            ProductiveUnit.deleted_at.is_(None),
        )
    ).all()
    visible = []
    for unit, _participation in rows:
        products = db.session.scalars(Product.publicable_query(unit.id)).all()
        if len(products) >= 3:
            visible.append((unit, products))
    return visible


def _public_product_payload(product, unit=None):
    from ..esquemas.productos import productive_product_json

    payload = productive_product_json(product)
    if unit:
        payload["unidad_productiva"] = {
            "id": str(unit.id), "nombre_comercial": unit.nombre_comercial,
            "telefono_whatsapp": unit.telefono_whatsapp,
        }
    return payload


def _public_unit_payload(unit, products, include_products=False):
    from ..serializadores.dominio import productive_unit_json

    payload = productive_unit_json(unit)
    for key in ("user_id", "registration_request_id", "nit"):
        payload.pop(key, None)
    if include_products:
        payload["productos"] = [_public_product_payload(product) for product in products]
    payload["cantidad_productos_publicables"] = len(products)
    return payload


def _slice_items(items):
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = max(1, min(100, int(request.args.get("per_page", 20))))
    except (TypeError, ValueError):
        page, per_page = 1, 20
    total = len(items)
    pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    return {
        "items": items[start:start + per_page],
        "pagination": {"page": page, "per_page": per_page, "pages": pages, "total": total,
                       "has_next": page < pages, "has_prev": page > 1},
    }


def _canonical_cache_key(resource):
    return ("canonical", resource, tuple(sorted(request.args.items())))


@public_bp.get("/public/fairs/active")
def canonical_active_fair():
    fairs = _active_canonical_fairs()
    fair = fairs[0] if fairs else None
    key = _canonical_cache_key("active-fair")
    cached = get_public_cache(key)
    if cached is not None:
        return cached
    term = (request.args.get("q") or "").strip().lower()
    if term:
        fairs = [item for item in fairs if term in " ".join(filter(None, (
            item.nombre, item.ubicacion, item.lugar, item.descripcion,
            item.departamento, item.municipio,
        ))).lower()]
    paginated = _slice_items([_canonical_fair_payload(item) for item in fairs])
    return set_public_cache(key, {
        "active": bool(fair),
        "fair": _canonical_fair_payload(fair) if fair else None,
        **paginated,
    })


@public_bp.get("/public/productive-units")
def canonical_public_units():
    from ..modelos import SectorStatus, UnitSector

    fair = _requested_canonical_fair()
    key = _canonical_cache_key("productive-units")
    cached = get_public_cache(key)
    if cached is not None:
        return cached
    if not fair:
        return set_public_cache(key, {"active_catalog": False, **_slice_items([])})
    term = (request.args.get("q") or "").strip().lower()
    department, sector_id = request.args.get("departamento"), request.args.get("sector_id")
    output = []
    for unit, products in _visible_canonical_units(fair):
        if term and term not in unit.nombre_comercial.lower() and not any(term in product.nombre_comercial.lower() for product in products):
            continue
        if department and unit.departamento != department:
            continue
        if sector_id and not db.session.scalar(select(UnitSector.id).where(
            UnitSector.productive_unit_id == unit.id,
            UnitSector.productive_sector_id == sector_id,
            UnitSector.estado == SectorStatus.ACTIVE,
        )):
            continue
        output.append(_public_unit_payload(unit, products))
    output.sort(key=lambda item: item["nombre_comercial"].lower(), reverse=request.args.get("order") == "name_desc")
    return set_public_cache(key, {"active_catalog": True, "fair": _canonical_fair_payload(fair), **_slice_items(output)})


@public_bp.get("/public/productive-units/<uuid:unit_id>")
def canonical_public_unit(unit_id):
    fair = _requested_canonical_fair()
    key = _canonical_cache_key(f"productive-unit:{unit_id}")
    cached = get_public_cache(key)
    if cached is not None:
        return cached
    if not fair:
        return error("No existe un catálogo activo", 404)
    for unit, products in _visible_canonical_units(fair):
        if unit.id == unit_id:
            return set_public_cache(key, _public_unit_payload(unit, products, include_products=True))
    return error("Unidad Productiva no encontrada", 404)


@public_bp.get("/public/products")
def canonical_public_products():
    from ..modelos import SectorStatus, UnitSector

    fair = _requested_canonical_fair()
    key = _canonical_cache_key("products")
    cached = get_public_cache(key)
    if cached is not None:
        return cached
    if not fair:
        return set_public_cache(key, {"active_catalog": False, **_slice_items([])})
    term, status = (request.args.get("q") or "").strip().lower(), request.args.get("estado")
    department, sector_id = request.args.get("departamento"), request.args.get("sector_id")
    output = []
    for unit, products in _visible_canonical_units(fair):
        requested_unit_id = request.args.get("productive_unit_id")
        if requested_unit_id and str(unit.id) != requested_unit_id:
            continue
        if department and unit.departamento != department:
            continue
        if sector_id and not db.session.scalar(
            select(UnitSector.id).where(
                UnitSector.productive_unit_id == unit.id,
                UnitSector.productive_sector_id == sector_id,
                UnitSector.estado == SectorStatus.ACTIVE,
            )
        ):
            continue
        for product in products:
            if term and term not in product.nombre_comercial.lower() and term not in unit.nombre_comercial.lower():
                continue
            if status and product.estado.value != status:
                continue
            output.append(_public_product_payload(product, unit))
    order = request.args.get("order", "name")
    sort_key = (lambda item: item["precio_referencia"]) if order in {"price", "price_desc"} else (lambda item: item["nombre_comercial"].lower())
    output.sort(key=sort_key, reverse=order in {"price_desc", "name_desc"})
    return set_public_cache(key, {"active_catalog": True, "fair": _canonical_fair_payload(fair), **_slice_items(output)})


@public_bp.get("/public/products/<uuid:product_id>")
def canonical_public_product(product_id):
    fair = _requested_canonical_fair()
    key = _canonical_cache_key(f"product:{product_id}")
    cached = get_public_cache(key)
    if cached is not None:
        return cached
    if not fair:
        return error("No existe un catálogo activo", 404)
    for unit, products in _visible_canonical_units(fair):
        for product in products:
            if product.id == product_id:
                return set_public_cache(key, _public_product_payload(product, unit))
    return error("Producto no encontrado", 404)


@public_bp.post("/public/whatsapp")
def canonical_whatsapp():
    from marshmallow import ValidationError
    from ..esquemas.portal_publico import PublicWhatsAppSchema

    try:
        data = PublicWhatsAppSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error("Datos inválidos", 400, exc.messages)
    fair_id = data.get("fair_id")
    fair = (
        db.session.scalar(Fair.active_query().where(Fair.id == fair_id))
        if fair_id
        else _active_canonical_fair()
    )
    if not fair:
        return error("No existe un catálogo activo", 409)
    visible_products, product_units = {}, {}
    for unit, products in _visible_canonical_units(fair):
        for product in products:
            visible_products[product.id], product_units[product.id] = product, unit
    quantities = {}
    for item in data["items"]:
        quantities[item["product_id"]] = quantities.get(item["product_id"], 0) + item["quantity"]
    if any(product_id not in visible_products for product_id in quantities):
        return error("Uno o más productos no están disponibles en el catálogo", 409)
    if len({product_units[product_id].id for product_id in quantities}) != 1:
        return error("Todos los productos deben pertenecer a la misma Unidad Productiva", 409)
    unit = product_units[next(iter(quantities))]
    product_lines = [
        f"• {visible_products[product_id].nombre_comercial} — Cantidad: {quantity}"
        for product_id, quantity in quantities.items()
    ]
    message = "\n".join(
        [
            f"Hola, vi sus productos en Ferias Productivas Bolivia ({fair.nombre}).",
            "",
            "Quisiera más información sobre los siguientes productos:",
            *product_lines,
            "",
            "Gracias.",
        ]
    )
    digits = "".join(character for character in unit.telefono_whatsapp if character.isdigit())
    if digits.startswith("0"):
        digits = "591" + digits.lstrip("0")
    elif len(digits) == 8:
        digits = "591" + digits
    return {"url": f"https://wa.me/{digits}?text={quote(message)}"}
