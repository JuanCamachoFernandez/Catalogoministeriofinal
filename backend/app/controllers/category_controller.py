from datetime import datetime, timezone

from flask import Blueprint, request
from sqlalchemy import func, select

from ..extensions import db
from ..models import Category, Product, Role
from ..utils import slugify
from ..views import error, paginate, validate_json, validated_json
from ..views.category_view import (
    CategoryCreateSchema,
    CategoryStatusSchema,
    CategoryUpdateSchema,
)
from .common import audit, invalidate_public_cache, roles

category_bp = Blueprint("categories", __name__)


def category_json(category):
    return {
        "id": str(category.id),
        "nombre": category.nombre,
        "slug": category.slug,
        "descripcion": category.descripcion,
        "estado": category.estado,
    }


@category_bp.get("/categories")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO, Role.EXPOSITOR)
def categories():
    query = (
        select(Category)
        .where(Category.estado.is_(True), Category.deleted_at.is_(None))
        .order_by(Category.nombre)
    )
    return paginate(query, category_json)


@category_bp.get("/admin/categories")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def admin_categories():
    query = select(Category).where(Category.deleted_at.is_(None))
    term = request.args.get("q", "").strip()
    if term:
        query = query.where(
            Category.nombre.ilike(f"%{term}%")
            | Category.descripcion.ilike(f"%{term}%")
        )
    if request.args.get("status") in {"active", "inactive"}:
        query = query.where(Category.estado.is_(request.args["status"] == "active"))
    query = query.order_by(Category.nombre)
    return paginate(query, category_json)


@category_bp.get("/categories/<uuid:category_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def get_category(category_id):
    category = db.session.get(Category, category_id)
    if not category or category.deleted_at:
        return error("Categoría no encontrada", 404)
    return category_json(category)


@category_bp.post("/categories")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(CategoryCreateSchema())
def create_category():
    data = validated_json()
    name = (data.get("nombre") or "").strip()
    if not name:
        return error("El nombre es obligatorio")
    if db.session.scalar(select(Category.id).where(func.lower(Category.nombre) == name.lower())):
        return error("La categoría ya existe", 409)
    category = Category(
        nombre=name,
        slug=slugify(name),
        descripcion=data.get("descripcion"),
        estado=True,
    )
    db.session.add(category)
    db.session.flush()
    audit("CREAR", "Categoria", category.id, f"Categoría creada: {category.nombre}")
    db.session.commit()
    invalidate_public_cache()
    return category_json(category), 201


@category_bp.patch("/categories/<uuid:category_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(CategoryUpdateSchema())
def update_category(category_id):
    category = db.session.get(Category, category_id)
    data = validated_json()
    if not category or category.deleted_at:
        return error("Categoría no encontrada", 404)
    if "nombre" in data:
        name = (data.get("nombre") or "").strip()
        if not name:
            return error("El nombre es obligatorio")
        duplicate = db.session.scalar(
            select(Category.id).where(
                func.lower(Category.nombre) == name.lower(), Category.id != category.id
            )
        )
        if duplicate:
            return error("La categoría ya existe", 409)
        category.nombre = name
        category.slug = slugify(name)
    if "descripcion" in data:
        category.descripcion = data.get("descripcion")
    audit("EDITAR", "Categoria", category.id, f"Categoría actualizada: {category.nombre}")
    db.session.commit()
    invalidate_public_cache()
    return category_json(category)


@category_bp.patch("/categories/<uuid:category_id>/status")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(CategoryStatusSchema())
def category_status(category_id):
    category = db.session.get(Category, category_id)
    if not category or category.deleted_at:
        return error("Categoría no encontrada", 404)
    category.estado = validated_json()["active"]
    state = "habilitada" if category.estado else "inhabilitada"
    audit(
        "CAMBIAR_ESTADO",
        "Categoria",
        category.id,
        f"Categoría {category.nombre} {state}",
    )
    db.session.commit()
    invalidate_public_cache()
    return category_json(category)


@category_bp.delete("/categories/<uuid:category_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def delete_category(category_id):
    category = db.session.get(Category, category_id)
    if not category or category.deleted_at:
        return error("Categoría no encontrada", 404)
    products = db.session.scalar(
        select(func.count()).select_from(Product).where(Product.category_id == category.id)
    )
    if products:
        return error("La categoría tiene productos asociados; inhabilítela", 409)
    category.deleted_at = datetime.now(timezone.utc)
    category.estado = False
    audit("ELIMINAR", "Categoria", category.id, f"Categoría eliminada: {category.nombre}")
    db.session.commit()
    invalidate_public_cache()
    return "", 204
