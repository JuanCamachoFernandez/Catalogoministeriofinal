from datetime import date, datetime, timezone
from pathlib import Path
import os
import uuid

from flask import Blueprint, request
from sqlalchemy import select

from ..extensions import db
from ..models import (
    AssignmentStatus,
    Exhibitor,
    Fair,
    FairExhibitor,
    FairImage,
    FairParticipation,
    FeriaStatus,
    Product,
    ProductiveUnit,
    ProductiveUnitStatus,
    Role,
    bolivia_today,
)
from ..utils import slugify
from ..views import (
    assignment_json,
    error,
    fair_json,
    paginate,
    validate_json,
    validated_json,
)
from ..views.fair_view import (
    AssignmentCreateSchema,
    AssignmentUpdateSchema,
    FairCreateSchema,
    FairStatusSchema,
    FairUpdateSchema,
    CanonicalFairCreateSchema,
    CanonicalFairUpdateSchema,
    ParticipationCreateSchema,
    ParticipationUpdateSchema,
)
from .common import (
    audit,
    current_user,
    delete_managed_upload,
    invalidate_public_cache,
    require_managed_upload,
    roles,
    save_upload,
)

fair_bp = Blueprint("fairs", __name__)


def validate_cover_reference(value):
    if not value:
        return
    require_managed_upload(value, "ferias")


def cleanup_fair_images(fair):
    urls = [fair.imagen_portada] if fair.imagen_portada else []
    images = db.session.scalars(
        select(FairImage).where(FairImage.fair_id == fair.id)
    ).all()
    urls.extend(image.url for image in images)
    for image in images:
        db.session.delete(image)
    fair.imagen_portada = None
    return list(dict.fromkeys(url for url in urls if url))


def sync_fair_lifecycle(today=None):
    today = today or bolivia_today()
    fairs = db.session.scalars(Fair.lifecycle_query()).all()
    files_to_delete = []
    changed = False
    for fair in fairs:
        expected = fair.expected_status(today)
        if expected == fair.estado and fair.visible_publicamente == (
            expected == FeriaStatus.PUBLISHED
        ):
            continue
        previous = fair.estado
        fair.estado = expected
        fair.visible_publicamente = expected == FeriaStatus.PUBLISHED
        if expected == FeriaStatus.FINISHED:
            fair.finished_at = datetime.now(timezone.utc)
            files_to_delete.extend(cleanup_fair_images(fair))
        audit(
            "SINCRONIZAR_ESTADO",
            "Feria",
            fair.id,
            f"Estado automático {previous.value} -> {expected.value}",
        )
        changed = True
    if changed:
        db.session.commit()
        for url in files_to_delete:
            delete_managed_upload(url, "ferias")
        invalidate_public_cache()
    return changed


def parse_fair_dates(data, fair=None):
    try:
        start_value = data.get("fecha_inicio") or (fair.fecha_inicio if fair else None)
        end_value = data.get("fecha_fin") or (fair.fecha_fin if fair else None)
        start = start_value if isinstance(start_value, date) else date.fromisoformat(start_value)
        end = end_value if isinstance(end_value, date) else date.fromisoformat(end_value)
    except (ValueError, TypeError) as exc:
        raise ValueError("Las fechas son obligatorias y deben ser válidas") from exc
    if end < start:
        raise ValueError("La fecha final no puede ser anterior a la inicial")
    return start, end


def unique_fair_slug(name, fair_id=None):
    base = slugify(name)
    candidate = base
    number = 1
    query = select(Fair.id).where(Fair.slug == candidate)
    if fair_id:
        query = query.where(Fair.id != fair_id)
    while db.session.scalar(query):
        candidate = f"{base}-{number}"
        number += 1
        query = select(Fair.id).where(Fair.slug == candidate)
        if fair_id:
            query = query.where(Fair.id != fair_id)
    return candidate


@fair_bp.get("/fairs")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def list_fairs():
    sync_fair_lifecycle()
    term = request.args.get("q", "").strip()
    state = request.args.get("estado")
    parsed_state = None
    if state:
        try:
            parsed_state = FeriaStatus(state)
        except ValueError:
            return error("Estado de feria inválido")
    query = Fair.admin_query(term, parsed_state)
    if request.args.get("departamento"):
        query = query.where(Fair.departamento == request.args["departamento"])
    try:
        date_from = date.fromisoformat(request.args["date_from"]) if request.args.get("date_from") else None
        date_to = date.fromisoformat(request.args["date_to"]) if request.args.get("date_to") else None
    except ValueError:
        return error("Rango de fechas inválido")
    if date_from:
        query = query.where(Fair.fecha_fin >= date_from)
    if date_to:
        query = query.where(Fair.fecha_inicio <= date_to)
    return paginate(query.order_by(Fair.fecha_inicio.desc()), fair_json)


@fair_bp.get("/fairs/<uuid:fair_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def get_fair(fair_id):
    sync_fair_lifecycle()
    fair = db.session.get(Fair, fair_id)
    if not fair or fair.deleted_at:
        return error("Feria no encontrada", 404)
    return fair_json(fair)


@fair_bp.post("/fairs")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(FairCreateSchema())
def create_fair():
    data = validated_json()
    try:
        start, end = parse_fair_dates(data)
        validate_cover_reference(data.get("imagen_portada"))
    except ValueError as exc:
        return error(str(exc))
    required = (
        data.get("nombre"),
        data.get("lugar"),
        data.get("departamento"),
    )
    if _overlapping_fair(start, end):
        return error("El rango de fechas se superpone con otra feria", 409)
    if not all(required):
        return error("Nombre y ubicación son obligatorios")
    fair = Fair(
        nombre=data["nombre"].strip(),
        slug=unique_fair_slug(data["nombre"]),
        descripcion=data.get("descripcion"),
        lugar=data["lugar"].strip(),
        direccion=data.get("direccion"),
        departamento=data["departamento"],
        fecha_inicio=start,
        fecha_fin=end,
        imagen_portada=data.get("imagen_portada"),
        observaciones=data.get("observaciones"),
        created_by=current_user().id,
    )
    fair.estado = fair.expected_status()
    fair.visible_publicamente = fair.estado == FeriaStatus.PUBLISHED
    db.session.add(fair)
    db.session.flush()
    audit("CREAR", "Feria", fair.id, f"Feria creada: {fair.nombre}")
    db.session.commit()
    invalidate_public_cache()
    return fair_json(fair), 201


@fair_bp.patch("/fairs/<uuid:fair_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(FairUpdateSchema())
def update_fair(fair_id):
    sync_fair_lifecycle()
    fair = db.session.get(Fair, fair_id)
    data = validated_json()
    if not fair or fair.deleted_at:
        return error("Feria no encontrada", 404)
    if fair.terminal:
        return error("Una feria finalizada o cancelada no puede editarse", 409)
    try:
        start, end = parse_fair_dates(data, fair)
    except ValueError as exc:
        return error(str(exc))
    today = bolivia_today()
    if fair.estado == FeriaStatus.PUBLISHED and start > today:
        return error("Una feria publicada no puede regresar a preparación")
    if fair.estado == FeriaStatus.PUBLISHED and end < today:
        return error("Use la finalización manual para cerrar la feria")
    if _overlapping_fair(start, end, fair.id):
        return error("El rango de fechas se superpone con otra feria", 409)
    old_cover = None
    if "imagen_portada" in data and data.get("imagen_portada") != fair.imagen_portada:
        try:
            validate_cover_reference(data.get("imagen_portada"))
        except ValueError as exc:
            return error(str(exc))
        old_cover = fair.imagen_portada
    fair.fecha_inicio = start
    fair.fecha_fin = end
    for field in (
        "nombre",
        "descripcion",
        "lugar",
        "direccion",
        "departamento",
        "imagen_portada",
        "observaciones",
    ):
        if field in data:
            setattr(fair, field, data.get(field))
    if "nombre" in data:
        fair.slug = unique_fair_slug(fair.nombre, fair.id)
    fair.estado = fair.expected_status(today)
    fair.visible_publicamente = fair.estado == FeriaStatus.PUBLISHED
    audit("EDITAR", "Feria", fair.id, f"Feria actualizada: {fair.nombre}")
    db.session.commit()
    if old_cover:
        delete_managed_upload(old_cover, "ferias")
    invalidate_public_cache()
    return fair_json(fair)


@fair_bp.patch("/fairs/<uuid:fair_id>/status")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(FairStatusSchema())
def change_fair_status(fair_id):
    sync_fair_lifecycle()
    fair = db.session.get(Fair, fair_id)
    if not fair or fair.deleted_at:
        return error("Feria no encontrada", 404)
    if fair.terminal:
        return error("La feria ya tiene un estado terminal", 409)
    try:
        status = FeriaStatus(validated_json()["status"])
    except ValueError:
        return error("Estado de feria inválido")
    if status not in (FeriaStatus.FINISHED, FeriaStatus.DISABLED):
        return error("La publicación de ferias se determina automáticamente por fechas")
    fair.estado = status
    fair.visible_publicamente = False
    urls = cleanup_fair_images(fair)
    audit(
        "CAMBIAR_ESTADO", "Feria", fair.id,
        f"Estado de {fair.nombre} cambiado a {status.value}",
    )
    db.session.commit()
    for url in urls:
        delete_managed_upload(url, "ferias")
    invalidate_public_cache()
    return fair_json(fair)


@fair_bp.get("/fairs/<uuid:fair_id>/images")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def list_fair_images(fair_id):
    fair = db.session.get(Fair, fair_id)
    if not fair:
        return error("Feria no encontrada", 404)
    query = (
        select(FairImage)
        .where(FairImage.fair_id == fair_id)
        .order_by(FairImage.display_order)
    )
    return paginate(
        query,
        lambda image: {
            "id": str(image.id),
            "url": image.url,
            "alt_text": image.alt_text,
            "display_order": image.display_order,
        },
    )


@fair_bp.post("/fairs/<uuid:fair_id>/images")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def add_fair_image(fair_id):
    sync_fair_lifecycle()
    fair = db.session.get(Fair, fair_id)
    if not fair or fair.deleted_at:
        return error("Feria no encontrada", 404)
    if fair.terminal:
        return error("No se pueden agregar imágenes a una feria terminal", 409)
    try:
        url = save_upload(request.files.get("file"), "ferias")
    except ValueError as exc:
        return error(str(exc))
    if not url:
        return error("Debe enviar una imagen")
    image = FairImage(
        fair_id=fair.id,
        filename=os.path.basename(url),
        url=url,
        alt_text=request.form.get("alt_text"),
        display_order=int(request.form.get("display_order") or 0),
    )
    db.session.add(image)
    audit("AGREGAR_IMAGEN", "Feria", fair.id, f"Imagen agregada a la feria {fair.nombre}")
    db.session.commit()
    invalidate_public_cache()
    return {"id": str(image.id), "url": image.url}, 201


@fair_bp.delete("/fair-images/<uuid:image_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def delete_fair_image(image_id):
    image = db.session.get(FairImage, image_id)
    if not image:
        return error("Imagen no encontrada", 404)
    fair = db.session.get(Fair, image.fair_id)
    if fair.terminal:
        return error("La feria es inmutable", 409)
    url = image.url
    db.session.delete(image)
    audit("ELIMINAR_IMAGEN", "Feria", fair.id, f"Imagen eliminada de la feria {fair.nombre}")
    db.session.commit()
    delete_managed_upload(url, "ferias")
    invalidate_public_cache()
    return "", 204


@fair_bp.get("/fairs/<uuid:fair_id>/exhibitors")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
def fair_assignments(fair_id):
    fair = db.session.get(Fair, fair_id)
    if not fair:
        return error("Feria no encontrada", 404)
    query = FairExhibitor.for_fair_query(fair_id).order_by(
        FairExhibitor.created_at.desc()
    )
    return paginate(query, assignment_json)


@fair_bp.post("/fairs/<uuid:fair_id>/exhibitors")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(AssignmentCreateSchema())
def assign_exhibitor(fair_id):
    sync_fair_lifecycle()
    fair = db.session.get(Fair, fair_id)
    data = validated_json()
    if not fair or fair.deleted_at:
        return error("Feria no encontrada", 404)
    if fair.terminal:
        return error("No se puede modificar una feria terminal", 409)
    try:
        value = data.get("exhibitor_id")
        exhibitor_id = value if isinstance(value, uuid.UUID) else uuid.UUID(value or "")
    except (ValueError, TypeError):
        return error("Expositor inválido")
    exhibitor = db.session.get(Exhibitor, exhibitor_id)
    if not exhibitor or exhibitor.deleted_at:
        return error("Expositor no encontrado", 404)
    existing = db.session.scalar(
        select(FairExhibitor).where(
            FairExhibitor.fair_id == fair_id,
            FairExhibitor.exhibitor_id == exhibitor_id,
        )
    )
    if existing:
        return error("El expositor ya está asignado a la feria", 409)
    try:
        status = AssignmentStatus(data.get("estado", "AUTHORIZED"))
    except ValueError:
        return error("Estado de asignación inválido")
    assignment = FairExhibitor(
        fair_id=fair_id,
        exhibitor_id=exhibitor_id,
        estado=status,
        numero_stand=data.get("numero_stand"),
        sector=data.get("sector"),
        observaciones=data.get("observaciones"),
    )
    if status == AssignmentStatus.AUTHORIZED:
        assignment.authorized_by = current_user().id
        assignment.authorized_at = datetime.now(timezone.utc)
    db.session.add(assignment)
    db.session.flush()
    audit("ASIGNAR", "FeriaExpositor", assignment.id, "Expositor asignado")
    db.session.commit()
    invalidate_public_cache()
    return assignment_json(assignment), 201


@fair_bp.patch("/fair-exhibitors/<uuid:assignment_id>")
@roles(Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO)
@validate_json(AssignmentUpdateSchema())
def update_assignment(assignment_id):
    sync_fair_lifecycle()
    assignment = db.session.get(FairExhibitor, assignment_id)
    data = validated_json()
    if not assignment:
        return error("Asignación no encontrada", 404)
    fair = db.session.get(Fair, assignment.fair_id)
    if fair.terminal:
        return error("No se puede modificar una feria terminal", 409)
    if "estado" in data:
        try:
            status = AssignmentStatus(data.get("estado"))
        except ValueError:
            return error("Estado de asignación inválido")
        assignment.estado = status
        if status == AssignmentStatus.AUTHORIZED:
            assignment.authorized_by = current_user().id
            assignment.authorized_at = datetime.now(timezone.utc)
    for field in ("numero_stand", "sector", "observaciones"):
        if field in data:
            setattr(assignment, field, data.get(field))
    audit("EDITAR", "FeriaExpositor", assignment.id, "Asignación actualizada")
    db.session.commit()
    invalidate_public_cache()
    return assignment_json(assignment)


CANONICAL_ADMIN_ROLES = (Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO, Role.ADMIN)


def canonical_fair_json(fair):
    return {
        **fair_json(fair),
        "ubicacion": fair.ubicacion or fair.lugar,
        "fecha_registro": fair.created_at.isoformat(),
        "fecha_actualizacion": fair.updated_at.isoformat(),
        "disabled_at": fair.disabled_at.isoformat() if fair.disabled_at else None,
        "finished_at": fair.finished_at.isoformat() if fair.finished_at else None,
    }


def participation_json(item):
    unit = db.session.get(ProductiveUnit, item.productive_unit_id)
    return {
        "id": str(item.id),
        "fair_id": str(item.fair_id),
        "productive_unit_id": str(item.productive_unit_id),
        "nombre_comercial": unit.nombre_comercial if unit else None,
        "estado": item.estado.value,
        "observaciones": item.observaciones,
        "fecha_registro": item.created_at.isoformat(),
        "fecha_actualizacion": item.updated_at.isoformat(),
        "authorized_at": item.authorized_at.isoformat() if item.authorized_at else None,
        "revoked_at": item.revoked_at.isoformat() if item.revoked_at else None,
    }


def _overlapping_fair(start, end, fair_id=None):
    query = select(Fair.id).where(
        Fair.deleted_at.is_(None),
        Fair.estado.notin_([FeriaStatus.FINISHED, FeriaStatus.DISABLED]),
        Fair.fecha_inicio <= end,
        Fair.fecha_fin >= start,
    )
    if fair_id:
        query = query.where(Fair.id != fair_id)
    return db.session.scalar(query)


@fair_bp.get("/admin/fairs")
@roles(*CANONICAL_ADMIN_ROLES)
def canonical_list_fairs():
    sync_fair_lifecycle()
    query = Fair.admin_query(request.args.get("q", "").strip(), None)
    if request.args.get("estado"):
        try:
            query = query.where(Fair.estado == FeriaStatus(request.args["estado"]))
        except ValueError:
            return error("Estado de feria inválido")
    try:
        date_from = (
            date.fromisoformat(request.args["date_from"])
            if request.args.get("date_from")
            else None
        )
        date_to = (
            date.fromisoformat(request.args["date_to"])
            if request.args.get("date_to")
            else None
        )
    except ValueError:
        return error("Rango de fechas inválido")
    if date_from:
        query = query.where(Fair.fecha_fin >= date_from)
    if date_to:
        query = query.where(Fair.fecha_inicio <= date_to)
    return paginate(query.order_by(Fair.fecha_inicio.desc()), canonical_fair_json)


@fair_bp.post("/admin/fairs")
@roles(*CANONICAL_ADMIN_ROLES)
@validate_json(CanonicalFairCreateSchema())
def canonical_create_fair():
    data = validated_json()
    fair = Fair(
        nombre=data["nombre"].strip(),
        slug=unique_fair_slug(data["nombre"]),
        descripcion=data.get("descripcion"),
        ubicacion=data["ubicacion"].strip(),
        lugar=data["ubicacion"].strip(),
        departamento=data["departamento"],
        fecha_inicio=data["fecha_inicio"],
        fecha_fin=data["fecha_fin"],
        created_by=current_user().id,
    )
    fair.estado = fair.expected_status()
    fair.visible_publicamente = fair.estado == FeriaStatus.PUBLISHED
    db.session.add(fair)
    db.session.flush()
    audit("CREAR", "Fair", fair.id)
    db.session.commit()
    invalidate_public_cache()
    return canonical_fair_json(fair), 201


@fair_bp.get("/admin/fairs/<uuid:fair_id>")
@roles(*CANONICAL_ADMIN_ROLES)
def canonical_get_fair(fair_id):
    sync_fair_lifecycle()
    fair = db.session.get(Fair, fair_id)
    return canonical_fair_json(fair) if fair and not fair.deleted_at else error("Feria no encontrada", 404)


@fair_bp.patch("/admin/fairs/<uuid:fair_id>")
@roles(*CANONICAL_ADMIN_ROLES)
@validate_json(CanonicalFairUpdateSchema())
def canonical_update_fair(fair_id):
    sync_fair_lifecycle()
    fair = db.session.get(Fair, fair_id)
    if not fair or fair.deleted_at:
        return error("Feria no encontrada", 404)
    if fair.terminal:
        return error("Una feria terminal es inmutable", 409)
    data = validated_json()
    start = data.get("fecha_inicio", fair.fecha_inicio)
    end = data.get("fecha_fin", fair.fecha_fin)
    if end < start:
        return error("La fecha final no puede ser anterior a la inicial")
    if fair.estado == FeriaStatus.PUBLISHED and start > bolivia_today():
        return error("Una feria publicada no puede regresar a preparación", 409)
    for key in ("nombre", "descripcion", "departamento", "fecha_inicio", "fecha_fin"):
        if key in data:
            setattr(fair, key, data[key])
    if "ubicacion" in data:
        fair.ubicacion = fair.lugar = data["ubicacion"]
    if "nombre" in data:
        fair.slug = unique_fair_slug(fair.nombre, fair.id)
    audit("EDITAR", "Fair", fair.id)
    db.session.commit()
    sync_fair_lifecycle()
    invalidate_public_cache()
    return canonical_fair_json(fair)


def _terminal_fair(fair_id, status):
    sync_fair_lifecycle()
    fair = db.session.get(Fair, fair_id)
    if not fair or fair.deleted_at:
        return error("Feria no encontrada", 404)
    if fair.terminal:
        return error("La feria ya tiene un estado terminal", 409)
    now_value = datetime.now(timezone.utc)
    fair.estado = status
    fair.visible_publicamente = False
    now_value = datetime.now(timezone.utc)
    fair.disabled_at = now_value if status == FeriaStatus.DISABLED else None
    fair.finished_at = now_value if status == FeriaStatus.FINISHED else None
    fair.disabled_at = now_value if status == FeriaStatus.DISABLED else None
    fair.finished_at = now_value if status == FeriaStatus.FINISHED else None
    urls = cleanup_fair_images(fair)
    audit("CAMBIAR_ESTADO", "Fair", fair.id)
    db.session.commit()
    for url in urls:
        delete_managed_upload(url, "ferias")
    invalidate_public_cache()
    return canonical_fair_json(fair)


@fair_bp.post("/admin/fairs/<uuid:fair_id>/publish")
@roles(*CANONICAL_ADMIN_ROLES)
def canonical_publish_fair(fair_id):
    sync_fair_lifecycle()
    fair = db.session.get(Fair, fair_id)
    if not fair or fair.deleted_at:
        return error("Feria no encontrada", 404)
    if fair.terminal:
        return error("Una feria terminal no puede reactivarse", 409)
    if fair.expected_status() != FeriaStatus.PUBLISHED:
        return error("La feria solo se publica automáticamente dentro de sus fechas", 409)
    fair.estado = FeriaStatus.PUBLISHED
    fair.visible_publicamente = True
    audit("CAMBIAR_ESTADO", "Fair", fair.id, after={"estado": "PUBLISHED"})
    db.session.commit()
    invalidate_public_cache()
    return canonical_fair_json(fair)


@fair_bp.post("/admin/fairs/<uuid:fair_id>/disable")
@roles(*CANONICAL_ADMIN_ROLES)
def canonical_disable_fair(fair_id):
    return _terminal_fair(fair_id, FeriaStatus.DISABLED)


@fair_bp.post("/admin/fairs/<uuid:fair_id>/finish")
@roles(*CANONICAL_ADMIN_ROLES)
def canonical_finish_fair(fair_id):
    return _terminal_fair(fair_id, FeriaStatus.FINISHED)


@fair_bp.post("/admin/fairs/<uuid:fair_id>/cover")
@roles(*CANONICAL_ADMIN_ROLES)
def canonical_upload_cover(fair_id):
    fair = db.session.get(Fair, fair_id)
    if not fair or fair.deleted_at:
        return error("Feria no encontrada", 404)
    if fair.terminal:
        return error("Una feria terminal es inmutable", 409)
    try:
        url = save_upload(request.files.get("file"), "ferias")
    except ValueError as exc:
        return error(str(exc))
    if not url:
        return error("Debe enviar una imagen")
    previous = fair.imagen_portada
    fair.imagen_portada = url
    audit(
        "AGREGAR_IMAGEN",
        "Fair",
        fair.id,
        before={"imagen_portada": previous},
        after={"imagen_portada": url},
    )
    db.session.commit()
    delete_managed_upload(previous, "ferias")
    invalidate_public_cache()
    return {"imagen_portada": url}, 201


@fair_bp.delete("/admin/fairs/<uuid:fair_id>/cover")
@roles(*CANONICAL_ADMIN_ROLES)
def canonical_delete_cover(fair_id):
    fair = db.session.get(Fair, fair_id)
    if not fair or fair.deleted_at:
        return error("Feria no encontrada", 404)
    if fair.terminal:
        return error("Una feria terminal es inmutable", 409)
    previous = fair.imagen_portada
    fair.imagen_portada = None
    audit(
        "ELIMINAR_IMAGEN",
        "Fair",
        fair.id,
        before={"imagen_portada": previous},
        after={"imagen_portada": None},
    )
    db.session.commit()
    delete_managed_upload(previous, "ferias")
    invalidate_public_cache()
    return {"message": "Portada eliminada"}


def _participation_context(fair_id, participation_id=None):
    fair = db.session.get(Fair, fair_id)
    item = db.session.get(FairParticipation, participation_id) if participation_id else None
    if item and item.fair_id != fair_id:
        item = None
    return fair, item


@fair_bp.get("/admin/fairs/<uuid:fair_id>/participations")
@roles(*CANONICAL_ADMIN_ROLES)
def canonical_list_participations(fair_id):
    fair = db.session.get(Fair, fair_id)
    if not fair:
        return error("Feria no encontrada", 404)
    return paginate(FairParticipation.for_fair_query(fair_id).order_by(FairParticipation.created_at.desc()), participation_json)


@fair_bp.post("/admin/fairs/<uuid:fair_id>/participations")
@roles(*CANONICAL_ADMIN_ROLES)
@validate_json(ParticipationCreateSchema())
def canonical_create_participation(fair_id):
    sync_fair_lifecycle()
    fair = db.session.get(Fair, fair_id)
    if not fair or fair.deleted_at:
        return error("Feria no encontrada", 404)
    if fair.terminal:
        return error("No se puede modificar una feria terminal", 409)
    data = validated_json()
    unit = db.session.get(ProductiveUnit, data["productive_unit_id"])
    if not unit or unit.deleted_at:
        return error("Unidad Productiva no encontrada", 404)
    existing = db.session.scalar(select(FairParticipation.id).where(FairParticipation.fair_id == fair.id, FairParticipation.productive_unit_id == unit.id))
    if existing:
        return error("La Unidad Productiva ya participa en la feria", 409)
    item = FairParticipation(fair_id=fair.id, productive_unit_id=unit.id, observaciones=data.get("observaciones"), estado=AssignmentStatus.PENDING)
    db.session.add(item)
    db.session.flush()
    audit("ASIGNAR", "FairParticipation", item.id)
    db.session.commit()
    invalidate_public_cache()
    return participation_json(item), 201


@fair_bp.get("/admin/fairs/<uuid:fair_id>/participations/<uuid:participation_id>")
@roles(*CANONICAL_ADMIN_ROLES)
def canonical_get_participation(fair_id, participation_id):
    fair, item = _participation_context(fair_id, participation_id)
    return participation_json(item) if fair and item else error("Participación no encontrada", 404)


@fair_bp.patch("/admin/fairs/<uuid:fair_id>/participations/<uuid:participation_id>")
@roles(*CANONICAL_ADMIN_ROLES)
@validate_json(ParticipationUpdateSchema())
def canonical_update_participation(fair_id, participation_id):
    fair, item = _participation_context(fair_id, participation_id)
    if not fair or not item:
        return error("Participación no encontrada", 404)
    if fair.terminal:
        return error("No se puede modificar una feria terminal", 409)
    item.observaciones = validated_json().get("observaciones")
    audit("EDITAR", "FairParticipation", item.id)
    db.session.commit()
    return participation_json(item)


@fair_bp.delete("/admin/fairs/<uuid:fair_id>/participations/<uuid:participation_id>")
@roles(*CANONICAL_ADMIN_ROLES)
def canonical_delete_participation(fair_id, participation_id):
    fair, item = _participation_context(fair_id, participation_id)
    if not fair or not item:
        return error("Participación no encontrada", 404)
    if fair.terminal:
        return error("No se puede modificar una feria terminal", 409)
    item.estado = AssignmentStatus.INACTIVE
    item.revoked_at = datetime.now(timezone.utc)
    audit("CAMBIAR_ESTADO", "FairParticipation", item.id, after={"estado": "INACTIVE"})
    db.session.commit()
    invalidate_public_cache()
    return "", 204


@fair_bp.post("/admin/fairs/<uuid:fair_id>/participations/<uuid:participation_id>/authorize")
@roles(*CANONICAL_ADMIN_ROLES)
def canonical_authorize_participation(fair_id, participation_id):
    sync_fair_lifecycle()
    fair, item = _participation_context(fair_id, participation_id)
    if not fair or not item:
        return error("Participación no encontrada", 404)
    if fair.terminal:
        return error("No se puede modificar una feria terminal", 409)
    unit = db.session.get(ProductiveUnit, item.productive_unit_id)
    if not unit or unit.deleted_at or unit.estado != ProductiveUnitStatus.ACTIVE:
        return error("La Unidad Productiva no está activa", 409)
    publicable_count = len(db.session.scalars(Product.publicable_query(unit.id)).all())
    if publicable_count < 3:
        return error("Se requieren al menos tres productos publicables", 409)
    item.estado = AssignmentStatus.AUTHORIZED
    item.authorized_by = current_user().id
    item.authorized_at = datetime.now(timezone.utc)
    item.revoked_at = None
    audit("AUTORIZAR", "FairParticipation", item.id)
    db.session.commit()
    invalidate_public_cache()
    return participation_json(item)


@fair_bp.post("/admin/fairs/<uuid:fair_id>/participations/<uuid:participation_id>/revoke")
@roles(*CANONICAL_ADMIN_ROLES)
def canonical_revoke_participation(fair_id, participation_id):
    fair, item = _participation_context(fair_id, participation_id)
    if not fair or not item:
        return error("Participación no encontrada", 404)
    if fair.terminal:
        return error("No se puede modificar una feria terminal", 409)
    item.estado = AssignmentStatus.REVOKED
    item.revoked_at = datetime.now(timezone.utc)
    audit("REVOCAR", "FairParticipation", item.id)
    db.session.commit()
    invalidate_public_cache()
    return participation_json(item)
