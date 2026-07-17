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
    FeriaStatus,
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
        require_managed_upload(data.get("imagen_portada"), "ferias")
    except ValueError as exc:
        return error(str(exc))
    required = (
        data.get("nombre"),
        data.get("lugar"),
        data.get("departamento"),
        data.get("municipio"),
    )
    if not all(required):
        return error("Nombre y ubicación son obligatorios")
    Fair.acquire_schedule_lock()
    if Fair.has_overlap(start, end):
        return error("Las fechas se superponen con otra feria", 409)
    fair = Fair(
        nombre=data["nombre"].strip(),
        slug=unique_fair_slug(data["nombre"]),
        descripcion=data.get("descripcion"),
        lugar=data["lugar"].strip(),
        direccion=data.get("direccion"),
        departamento=data["departamento"],
        municipio=data["municipio"],
        fecha_inicio=start,
        fecha_fin=end,
        imagen_portada=data["imagen_portada"],
        observaciones=data.get("observaciones"),
        created_by=current_user().id,
    )
    fair.estado = fair.expected_status()
    fair.visible_publicamente = fair.estado == FeriaStatus.PUBLISHED
    db.session.add(fair)
    db.session.flush()
    audit("CREAR", "Feria", fair.id, "Feria creada")
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
    Fair.acquire_schedule_lock()
    if Fair.has_overlap(start, end, fair.id):
        return error("Las fechas se superponen con otra feria", 409)
    old_cover = None
    if "imagen_portada" in data and data.get("imagen_portada") != fair.imagen_portada:
        try:
            require_managed_upload(data.get("imagen_portada"), "ferias")
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
        "municipio",
        "imagen_portada",
        "observaciones",
    ):
        if field in data:
            setattr(fair, field, data.get(field))
    if "nombre" in data:
        fair.slug = unique_fair_slug(fair.nombre, fair.id)
    fair.estado = fair.expected_status(today)
    fair.visible_publicamente = fair.estado == FeriaStatus.PUBLISHED
    audit("EDITAR", "Feria", fair.id, "Feria actualizada")
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
    audit("CAMBIAR_ESTADO", "Feria", fair.id, f"Estado cambiado a {status.value}")
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
    audit("AGREGAR_IMAGEN", "Feria", fair.id, "Imagen agregada")
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
    audit("ELIMINAR_IMAGEN", "Feria", fair.id)
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
