from urllib.parse import quote
import uuid

from flask import Blueprint, request
from sqlalchemy import select

from ..extensions import db
from ..models import (
    AssignmentStatus,
    Exhibitor,
    Fair,
    FairExhibitor,
    FeriaStatus,
    Product,
    ProductStatus,
    UserStatus,
)
from ..utils import normalize_whatsapp
from ..views import error, fair_json, product_json
from .fair_controller import sync_fair_lifecycle
from .common import get_public_cache, set_public_cache

public_bp = Blueprint("public", __name__)


def active_fair_query():
    return select(Fair).where(
        Fair.estado == FeriaStatus.PUBLISHED,
        Fair.visible_publicamente.is_(True),
        Fair.deleted_at.is_(None),
    )


def public_exhibitor_rows(fair_id):
    query = (
        select(Exhibitor, FairExhibitor)
        .join(FairExhibitor, FairExhibitor.exhibitor_id == Exhibitor.id)
        .where(
            FairExhibitor.fair_id == fair_id,
            FairExhibitor.estado == AssignmentStatus.AUTHORIZED,
            Exhibitor.estado == UserStatus.ACTIVE,
            Exhibitor.deleted_at.is_(None),
        )
    )
    term = request.args.get("q", "").strip()
    if term:
        query = query.where(Exhibitor.nombre_comercial.ilike(f"%{term}%"))
    if request.args.get("departamento"):
        query = query.where(Exhibitor.departamento == request.args["departamento"])
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
    query = active_fair_query()
    term = request.args.get("q")
    if term:
        query = query.where(Fair.nombre.ilike(f"%{term}%"))
    if request.args.get("departamento"):
        query = query.where(Fair.departamento == request.args["departamento"])
    items = db.session.scalars(query.order_by(Fair.fecha_inicio.desc())).all()
    return set_public_cache(cache_key, {"items": [fair_json(item) for item in items]})


@public_bp.get("/public/active-fair")
def public_active_fair():
    sync_fair_lifecycle()
    cache_key = ("active_fair", tuple(sorted(request.args.items())))
    if cached := get_public_cache(cache_key):
        return cached
    fair = db.session.scalar(active_fair_query().order_by(Fair.fecha_inicio.desc()))
    if not fair:
        return error("No existe una feria activa", 404)
    return set_public_cache(cache_key, public_fair_payload(fair))


@public_bp.get("/public/fairs/<slug>")
def public_fair(slug):
    sync_fair_lifecycle()
    cache_key = ("fair", slug, tuple(sorted(request.args.items())))
    if cached := get_public_cache(cache_key):
        return cached
    fair = db.session.scalar(active_fair_query().where(Fair.slug == slug))
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
        select(Fair, Exhibitor)
        .join(FairExhibitor, FairExhibitor.fair_id == Fair.id)
        .join(Exhibitor, Exhibitor.id == FairExhibitor.exhibitor_id)
        .where(
            Fair.slug == slug,
            Fair.estado == FeriaStatus.PUBLISHED,
            Fair.visible_publicamente.is_(True),
            FairExhibitor.exhibitor_id == exhibitor_id,
            FairExhibitor.estado == AssignmentStatus.AUTHORIZED,
            Exhibitor.estado == UserStatus.ACTIVE,
            Exhibitor.deleted_at.is_(None),
        )
    ).first()
    if not row:
        return error("Expositor no disponible en esta feria", 404)
    _, exhibitor = row
    query = select(Product).where(
        Product.exhibitor_id == exhibitor.id,
        Product.estado.in_([ProductStatus.AVAILABLE, ProductStatus.OUT_OF_STOCK]),
        Product.deleted_at.is_(None),
    )
    term = request.args.get("q", "").strip()
    if term:
        query = query.where(Product.nombre.ilike(f"%{term}%"))
    if request.args.get("category_id"):
        try:
            query = query.where(Product.category_id == uuid.UUID(request.args["category_id"]))
        except ValueError:
            return error("Categoría inválida")
    if request.args.get("availability"):
        try:
            state = ProductStatus(request.args["availability"])
        except ValueError:
            return error("Disponibilidad inválida")
        if state not in (ProductStatus.AVAILABLE, ProductStatus.OUT_OF_STOCK):
            return error("Disponibilidad inválida")
        query = query.where(Product.estado == state)
    products = db.session.scalars(query.order_by(Product.nombre)).all()
    payload = {
        "id": str(exhibitor.id),
        "nombre_comercial": exhibitor.nombre_comercial,
        "descripcion": exhibitor.descripcion,
        "productos": [product_json(product) for product in products],
    }
    return set_public_cache(cache_key, payload)


@public_bp.post("/public/whatsapp-query")
def whatsapp_query():
    sync_fair_lifecycle()
    data = request.get_json() or {}
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
            product_id = uuid.UUID(item.get("product_id", ""))
            quantity = int(item.get("quantity", 1))
            if quantity <= 0:
                raise ValueError
            quantities[product_id] = quantities.get(product_id, 0) + quantity
    except (ValueError, TypeError, AttributeError):
        return error("Productos o cantidades inválidos")
    products = db.session.scalars(
        select(Product).where(
            Product.id.in_(quantities),
            Product.estado == ProductStatus.AVAILABLE,
            Product.deleted_at.is_(None),
        )
    ).all()
    if len(products) != len(quantities):
        return error("Algún producto no está disponible")
    owners = {product.exhibitor_id for product in products}
    if len(owners) != 1:
        return error("La consulta solo puede contener productos de un mismo expositor")
    owner_id = owners.pop()
    exhibitor = db.session.get(Exhibitor, owner_id)
    assignment = db.session.scalar(
        select(FairExhibitor)
        .join(Fair)
        .where(
            Fair.slug == data.get("fair_slug"),
            Fair.estado == FeriaStatus.PUBLISHED,
            Fair.visible_publicamente.is_(True),
            FairExhibitor.exhibitor_id == owner_id,
            FairExhibitor.estado == AssignmentStatus.AUTHORIZED,
        )
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
        f"- {product.nombre} (cantidad: {quantities[product.id]})"
        for product in products
    )
    message = (
        "Hola, vi sus productos en el Catálogo Digital de Ferias y quisiera "
        f"consultar por:\n{lines}\n\nExpositor: {exhibitor.nombre_comercial}"
    )
    return {"url": f"https://wa.me/{phone}?text={quote(message)}"}
