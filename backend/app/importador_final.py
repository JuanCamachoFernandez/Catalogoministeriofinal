import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

import click
from flask.cli import with_appcontext
from sqlalchemy import select, text
from werkzeug.datastructures import FileStorage

from .extensiones import db
from .fuentes_importacion import (
    GoogleSource, MAX_PRODUCTS, _product_complete, build_plan, normalize, plan_sha256, sha,
)
from .modelos import (
    FinalImportEntityTrace, FinalImportRun, FinalImportSourceRow, Product, ProductImage,
    ProductStatus, ProductiveSector, ProductiveUnit, ProductiveUnitStatus,
    RegistrationRequest, RegistrationStatus, Role, SectorStatus, UnitSector, User, UserStatus,
)
from .servicios import delete_cloudinary_upload, upload_to_cloudinary
from .utilidades import slugify

TOKEN_DEFAULT = "/secrets/google-import-token.json"
LOCK_KEY = 7420192601
ACCEPTED_NON_BLOCKING_WARNINGS = {
    "producto_incompleto_draft",
    "producto_general_ambiguo",
    "fotografias_generales_ambiguas",
}


def write_json(path, payload):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)


def dry_run_summary_text(summary):
    """Render only aggregate counters; never echo source values or identifiers."""
    units = summary.get("unit_classification") or {}
    total_products = (summary.get("product_sources") or {}).get("total", {})
    total_images = (summary.get("image_sources") or {}).get("total", {})
    lines = [
        "UNIDADES",
        f"- importables completas: {units.get('importable_complete', 0)}",
        f"- importables incompletas: {units.get('importable_incomplete', 0)}",
        f"- pendientes estructurales: {units.get('structural_pending', 0)}",
        "", "PRODUCTOS",
        f"- importables: {total_products.get('importable', 0)}",
        f"- DRAFT por datos faltantes: {total_products.get('draft', 0)}",
        f"- pendientes por relacion no resoluble: {total_products.get('pending', 0)}",
        "", "IMAGENES",
        f"- asociadas: {total_images.get('assigned', 0)}",
        f"- pendientes/ambiguas: {total_images.get('ambiguous', 0)}",
        "", "PENDING BY REASON",
    ]
    pending_reasons = summary.get("pending_by_reason") or {}
    if pending_reasons:
        lines.extend(f"- {reason}: {count}" for reason, count in sorted(pending_reasons.items()))
    else:
        lines.append("- none: 0")
    lines.extend(("", "PENDING ROWS BY SOURCE"))
    for label, key in (("GENERAL", "general"), ("CORREGIDOS", "corrected")):
        lines.append(f"{label}:")
        source_pending = (summary.get("pending_rows") or {}).get(key, {})
        if source_pending:
            lines.extend(f"- {reason} -> filas {numbers}" for reason, numbers in sorted(source_pending.items()))
        else:
            lines.append("- none")
    lines.extend(("", "ERRORS BY REASON"))
    reasons = summary.get("errors_by_reason") or {}
    if reasons:
        lines.extend(f"- {reason}: {count}" for reason, count in sorted(reasons.items()))
    else:
        lines.append("- none: 0")
    lines.extend(("", "ERROR ROWS BY SOURCE"))
    for label, key in (("GENERAL", "general"), ("CORREGIDOS", "corrected")):
        lines.append(f"{label}:")
        source_errors = (summary.get("error_rows") or {}).get(key, {})
        if source_errors:
            lines.extend(f"- {reason} -> filas {numbers}" for reason, numbers in sorted(source_errors.items()))
        else:
            lines.append("- none")
    for label, key in (("GENERAL", "general"), ("CORREGIDOS", "corrected")):
        source = (summary.get("sources") or {}).get(key, {})
        lines.extend((
            "", f"{label}:",
            f"- filas leídas: {source.get('rows_read', 0)}",
            f"- válidas: {source.get('valid', 0)}",
            f"- inválidas: {source.get('invalid', 0)}",
        ))
    lines.extend(("", "WARNINGS BY REASON"))
    warning_reasons = summary.get("warnings_by_reason") or {}
    if warning_reasons:
        lines.extend(f"- {reason}: {count}" for reason, count in sorted(warning_reasons.items()))
    else:
        lines.append("- none: 0")
    severity = summary.get("warning_severity") or {}
    lines.extend((f"- bloqueantes: {severity.get('blocking', 0)}",
                  f"- informativas: {severity.get('informative', 0)}"))
    products = summary.get("product_sources") or {}
    general_products = products.get("general", {})
    corrected_products = products.get("corrected", {})
    total_products = products.get("total", {})
    lines.extend((
        "", "PRODUCTOS GENERAL",
        f"- detectados: {general_products.get('detected', 0)}",
        f"- válidos: {general_products.get('valid', 0)}",
        f"- draft: {general_products.get('draft', 0)}",
        f"- ambiguos: {general_products.get('ambiguous', 0)}",
        f"- descartados: {general_products.get('discarded', 0)}",
        "", "PRODUCTOS CORREGIDOS",
        f"- filas leídas: {corrected_products.get('rows_read', 0)}",
        f"- detectados: {corrected_products.get('detected', 0)}",
        f"- válidos: {corrected_products.get('valid', 0)}",
        f"- draft: {corrected_products.get('draft', 0)}",
        f"- inválidos: {corrected_products.get('invalid', 0)}",
        f"- sin unidad relacionada: {corrected_products.get('without_unit', 0)}",
        "", "TOTAL PRODUCTOS",
        f"- detectados: {total_products.get('detected', 0)}",
        f"- importables: {total_products.get('importable', 0)}",
        f"- draft: {total_products.get('draft', 0)}",
        f"- ambiguos: {total_products.get('ambiguous', 0)}",
    ))
    corrected_sectors = (summary.get("sector_sources") or {}).get("corrected", {})
    lines.extend((
        "", "SECTORES CORREGIDOS",
        f"- filas leídas: {corrected_sectors.get('rows_read', 0)}",
        f"- asociados: {corrected_sectors.get('associated', 0)}",
        f"- sin unidad relacionada: {corrected_sectors.get('without_unit', 0)}",
    ))
    images = summary.get("image_sources") or {}
    general_images = images.get("general", {})
    corrected_images = images.get("corrected", {})
    total_images = images.get("total", {})
    lines.extend((
        "", "IMÁGENES GENERAL",
        f"- logos detectados: {general_images.get('logos_detected', 0)}",
        f"- fotos detectadas: {general_images.get('photos_detected', 0)}",
        f"- fotos asignables: {general_images.get('assignable', 0)}",
        f"- fotos ambiguas: {general_images.get('ambiguous', 0)}",
        "", "IMÁGENES CORREGIDOS",
        f"- filas leídas: {corrected_images.get('rows_read', 0)}",
        f"- Drive IDs detectados: {corrected_images.get('drive_ids_detected', 0)}",
        f"- imágenes asociadas a producto: {corrected_images.get('assigned', 0)}",
        f"- imágenes sin producto: {corrected_images.get('without_product', 0)}",
        "", "TOTAL IMÁGENES",
        f"- logos: {total_images.get('logos', 0)}",
        f"- fotografías: {total_images.get('photos', 0)}",
        f"- fotografías asignadas: {total_images.get('assigned', 0)}",
        f"- fotografías ambiguas: {total_images.get('ambiguous', 0)}",
    ))
    lines.extend((
        "", "TOTAL:",
        f"- respuestas leídas: {summary.get('responses_read', 0)}",
        f"- unidades únicas válidas: {summary.get('unique_units', 0)}",
        f"- unidades inválidas: {summary.get('invalid_units', 0)}",
        f"- productos detectados: {summary.get('products_detected', 0)}",
        f"- errores: {summary.get('errors', 0)}",
        f"- advertencias: {summary.get('warnings', 0)}",
    ))
    return "\n".join(lines)


def unique_username(email):
    base = slugify(email.split("@")[0])[:60] or "responsable"
    candidate, suffix = base, 0
    while db.session.scalar(select(User.id).where(User.username == candidate)):
        suffix += 1
        candidate = f"{base[:70]}-{suffix}"
    return candidate


def existing_unit(payload):
    if len(payload.get("nit", "")) >= 5:
        item = db.session.scalar(select(ProductiveUnit).where(ProductiveUnit.nit == payload["nit"]))
        if item: return item
    if payload.get("email"):
        return db.session.scalar(select(ProductiveUnit).where(ProductiveUnit.correo_electronico == payload["email"]))
    return None


def persist_trace_rows(run, plan):
    row_models = {}
    trace_rows = plan.get("trace_rows")
    if trace_rows is None:
        trace_rows = []
        seen = set()
        for group in plan.get("units", []):
            for row in group.get("rows", []):
                key = (row["source"], row["worksheet"], row["row_number"])
                if key not in seen:
                    trace_rows.append({**row, "data": {}, "warnings": [], "ambiguous": False})
                    seen.add(key)
    for row in trace_rows:
        source_row = FinalImportSourceRow(
            run_id=run.id, source=row["source"], sheet_id=row["sheet_id"],
            worksheet=row["worksheet"], row_number=row["row_number"], row_hash=row["row_hash"],
            source_data=row.get("data") or {}, warnings=row.get("warnings") or [],
            is_ambiguous=bool(row.get("ambiguous")),
            pending_reasons=row.get("pending_reasons") or [], is_pending=bool(row.get("pending")),
        )
        db.session.add(source_row)
        db.session.flush()
        row_models[(row["source"], row["worksheet"], row["row_number"])] = source_row
    return row_models


def final_summary_text(summary):
    return "\n".join((
        "IMPORTACIÓN FINAL",
        f"- unidades creadas: {summary['units_created']}",
        f"- usuarios responsables creados: {summary['users_created']}",
        f"- sectores asociados: {summary['sectors_associated']}",
        f"- productos creados: {summary['products_created']}",
        f"- productos DRAFT: {summary['products_draft']}",
        f"- logos cargados: {summary['logos_uploaded']}",
        f"- imágenes de productos cargadas: {summary['product_images_uploaded']}",
        f"- registros ambiguos preservados: {summary['ambiguous_records_preserved']}",
        f"- registros pendientes preservados: {summary['pending_records_preserved']}",
        f"- errores: {summary['errors']}",
        f"- correos enviados: {summary['emails_sent']}",
    ))


def trace_entities(group, unit, product_entities, row_models):
    for row in group["rows"]:
        source_row = row_models[(row["source"], row["worksheet"], row["row_number"])]
        source_row.productive_unit_id = unit.id
        db.session.add(FinalImportEntityTrace(source_row_id=source_row.id, entity_type="PRODUCTIVE_UNIT",
                                             entity_id=unit.id, entity_key=str(unit.id)))
    for product, plan_product, images in product_entities:
        origin = plan_product["origin"]
        source_row = row_models[(origin["source"], origin["worksheet"], origin["row_number"])]
        db.session.add(FinalImportEntityTrace(source_row_id=source_row.id, entity_type="PRODUCT",
                                             entity_id=product.id, entity_key=normalize(product.nombre)))
        for image, drive_file_id in images:
            db.session.add(FinalImportEntityTrace(source_row_id=source_row.id, entity_type="PRODUCT_IMAGE",
                entity_id=image.id, entity_key=str(image.id), drive_file_id=drive_file_id))


def import_unit(group, google, row_models, uploaded, counters):
    payload = group["unit"]
    safe_phone = payload["phone"] if re.fullmatch(r"[67][0-9]{7}", payload.get("phone", "")) else ""
    safe_nit = payload.get("nit") if 5 <= len(payload.get("nit", "")) <= 12 else None
    unit = existing_unit(payload)
    if not unit:
            logo = None
            if payload.get("logo_drive_id"):
                filename, stream = google.download(payload["logo_drive_id"])
                logo = upload_to_cloudinary(FileStorage(stream=stream, filename=filename), "logos", "unit_logo")
                if logo and logo.get("public_id"): uploaded.append(logo["public_id"])
            user = User(username=unique_username(payload["email"]), email=payload["email"], role=Role.PRODUCTIVE_UNIT_RESPONSIBLE,
                first_name=payload["first_names"], last_name=payload["paternal_name"], apellido_paterno=payload["paternal_name"],
                apellido_materno=payload["maternal_name"], phone=safe_phone or None, status=UserStatus.ACTIVE,
                must_change_password=True)
            user.set_password(secrets.token_urlsafe(32))
            db.session.add(user)
            counters["users_created"] += 1
            common = dict(nombre_comercial=payload["business_name"], razon_social=payload["legal_name"], nit=safe_nit,
                registro_seprec=payload.get("seprec") or None, registro_pro_bolivia=payload.get("pro_bolivia") or None,
                nombres_representante=payload["first_names"], apellido_paterno_representante=payload["paternal_name"],
                apellido_materno_representante=payload["maternal_name"], departamento=payload["department"],
                direccion_fisica=payload["address"], telefono_whatsapp=safe_phone, correo_electronico=payload["email"],
                facebook_url=payload.get("facebook") or None, instagram_url=payload.get("instagram") or None,
                tiktok_url=payload.get("tiktok") or None, resena_comercial=payload["review"],
                logo_url=logo["url"] if logo else None, logo_public_id=logo["public_id"] if logo else None)
            request_item = RegistrationRequest(**common, estado=RegistrationStatus.APPROVED, fecha_revision=datetime.now(timezone.utc))
            db.session.add(request_item); db.session.flush()
            unit = ProductiveUnit(**common, user_id=user.id, registration_request_id=request_item.id,
                                  estado=ProductiveUnitStatus.ACTIVE, fecha_aprobacion=datetime.now(timezone.utc))
            db.session.add(unit); db.session.flush()
            counters["units_created"] += 1
            if logo:
                counters["logos_uploaded"] += 1
            for sector_name in payload.get("sectors", []):
                sector = db.session.scalar(select(ProductiveSector).where(ProductiveSector.nombre.ilike(sector_name)))
                if sector:
                    db.session.add(UnitSector(productive_unit_id=unit.id, productive_sector_id=sector.id, estado=SectorStatus.ACTIVE))
                    counters["sectors_associated"] += 1
    known = {normalize(name) for name in db.session.scalars(select(Product.nombre).where(Product.productive_unit_id == unit.id)).all()}
    entities = []
    for plan_product in group["products"]:
            key = normalize(plan_product["name"])
            if key in known or len(known) >= MAX_PRODUCTS: continue
            complete = _product_complete(plan_product)
            product = Product(productive_unit_id=unit.id, nombre=plan_product["name"], slug=slugify(plan_product["name"]),
                descripcion=plan_product.get("description") or "", nombre_comercial=plan_product["name"],
                descripcion_tecnica=plan_product.get("description") or None,
                materia_prima=plan_product.get("material") or None,
                dimensiones=plan_product.get("dimensions") or None,
                colores_disponibles=plan_product.get("colors") or None,
                certificaciones=plan_product.get("certifications") or None,
                presentacion=plan_product.get("presentation") or None,
                presentacion_empaque=plan_product.get("presentation") or None,
                precio_referencia=plan_product.get("price"), precio=plan_product.get("price"),
                capacidad_produccion_stock=plan_product.get("stock") or None,
                estado=ProductStatus.AVAILABLE if complete else ProductStatus.DRAFT)
            db.session.add(product); db.session.flush()
            counters["products_created"] += 1
            if not complete:
                counters["products_draft"] += 1
            images = []
            for order, drive_file_id in enumerate(plan_product.get("images", [])[:3]):
                filename, stream = google.download(drive_file_id)
                result = upload_to_cloudinary(FileStorage(stream=stream, filename=filename), "productos", "product")
                if result.get("public_id"): uploaded.append(result["public_id"])
                image = ProductImage(product_id=product.id, filename=result["filename"], url=result["url"],
                    public_id=result.get("public_id"), alt_text=product.nombre, is_cover=order == 0, display_order=order)
                db.session.add(image); db.session.flush(); images.append((image, drive_file_id))
                counters["product_images_uploaded"] += 1
            entities.append((product, plan_product, images)); known.add(key)
    trace_entities(group, unit, entities, row_models)


def execute_plan(plan, google, source_documents=None):
    if plan_sha256(plan) != plan.get("plan_hash"):
        raise click.ClickException("El archivo de plan fue alterado o está incompleto")
    if plan.get("summary", {}).get("errors", 0):
        raise click.ClickException("El plan contiene errores reales; no se escribio ningun dato")
    blocking_warnings = [
        warning for warning in plan.get("warnings", [])
        if warning.get("severity") == "blocking"
        and warning.get("reason") not in ACCEPTED_NON_BLOCKING_WARNINGS
    ]
    if blocking_warnings:
        raise click.ClickException("El plan contiene advertencias bloqueantes; no se escribio ningun dato")
    if source_documents is None:
        general = google.spreadsheet(plan["sources"]["general"]["sheet_id"])
        corrected = google.spreadsheet(plan["sources"]["corrected"]["sheet_id"])
    else:
        general, corrected = source_documents
    if sha(general) != plan["sources"]["general"]["hash"] or sha(corrected) != plan["sources"]["corrected"]["hash"]:
        raise click.ClickException("Una hoja cambió después del dry-run; genere un plan nuevo")
    if db.session.scalar(select(FinalImportRun.id).where(FinalImportRun.plan_hash == plan["plan_hash"])):
        raise click.ClickException("Este plan ya fue ejecutado; no se repetirá")
    postgres = db.engine.dialect.name == "postgresql"
    if postgres and not db.session.scalar(select(db.func.pg_try_advisory_lock(LOCK_KEY))):
        raise click.ClickException("Ya existe otra importación final en ejecución")
    uploaded = []
    try:
        run = FinalImportRun(plan_hash=plan["plan_hash"], general_sheet_id=plan["sources"]["general"]["sheet_id"],
            corrected_sheet_id=plan["sources"]["corrected"]["sheet_id"], general_sheet_hash=plan["sources"]["general"]["hash"],
            corrected_sheet_hash=plan["sources"]["corrected"]["hash"], status="RUNNING")
        db.session.add(run); db.session.flush()
        row_models = persist_trace_rows(run, plan)
        counters = {
            "units_created": 0, "users_created": 0, "sectors_associated": 0,
            "products_created": 0, "products_draft": 0, "logos_uploaded": 0,
            "product_images_uploaded": 0,
            "ambiguous_records_preserved": sum(row.is_ambiguous for row in row_models.values()),
            "pending_records_preserved": sum(row.is_pending for row in row_models.values()),
            "units_importable_complete": plan.get("summary", {}).get("unit_classification", {}).get("importable_complete", 0),
            "units_importable_incomplete": plan.get("summary", {}).get("unit_classification", {}).get("importable_incomplete", 0),
            "units_structural_pending": plan.get("summary", {}).get("unit_classification", {}).get("structural_pending", 0),
            "errors": 0, "emails_sent": 0,
        }
        for group in plan["units"]:
            import_unit(group, google, row_models, uploaded, counters)
        run.status = "COMPLETED"
        run.summary = counters
        run.finished_at = datetime.now(timezone.utc); db.session.commit()
        return {"plan_hash": plan["plan_hash"], "status": run.status, "summary": counters}
    except Exception as exc:
        db.session.rollback()
        for public_id in reversed(uploaded):
            try:
                delete_cloudinary_upload(public_id)
            except Exception:
                pass
        if isinstance(exc, click.ClickException):
            raise
        raise click.ClickException(f"La importacion fue revertida: {type(exc).__name__}") from exc
    finally:
        if postgres:
            db.session.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK_KEY}); db.session.commit()


def register_import_command(app):
    @app.cli.command("importar-datos-finales")
    @click.option("--sheet-general")
    @click.option("--sheet-corregidos")
    @click.option("--dry-run", is_flag=True)
    @click.option("--commit", "do_commit", is_flag=True)
    @click.option("--plan", "plan_path", type=click.Path(dir_okay=False))
    @click.option("--expect-plan-sha256")
    @click.option("--confirm")
    @click.option("--report", "report_path", type=click.Path(dir_okay=False))
    @click.option("--token", "token_path", default=lambda: os.getenv("GOOGLE_IMPORT_TOKEN_PATH", TOKEN_DEFAULT), show_default=True)
    @with_appcontext
    def importar_datos_finales(sheet_general, sheet_corregidos, dry_run, do_commit, plan_path,
                               expect_plan_sha256, confirm, report_path, token_path):
        if dry_run == do_commit: raise click.ClickException("Seleccione exactamente uno: --dry-run o --commit")
        if dry_run:
            google = GoogleSource(token_path)
            if not sheet_general or not sheet_corregidos:
                raise click.ClickException("--sheet-general y --sheet-corregidos son obligatorios en dry-run")
            plan = build_plan(google.spreadsheet(sheet_general), google.spreadsheet(sheet_corregidos), sheet_general, sheet_corregidos)
            if report_path:
                write_json(report_path, plan)
            click.echo(dry_run_summary_text(plan["summary"]))
            click.echo(f"PLAN_SHA256: {plan['plan_hash']}")
        else:
            if confirm != "IMPORT-FINAL":
                raise click.ClickException("--confirm IMPORT-FINAL es obligatorio con --commit")
            google = GoogleSource(token_path)
            source_documents = None
            if plan_path:
                plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
            else:
                if not sheet_general or not sheet_corregidos or not expect_plan_sha256:
                    raise click.ClickException(
                        "--sheet-general, --sheet-corregidos y --expect-plan-sha256 son obligatorios con --commit"
                    )
                general = google.spreadsheet(sheet_general)
                corrected = google.spreadsheet(sheet_corregidos)
                source_documents = (general, corrected)
                plan = build_plan(general, corrected, sheet_general, sheet_corregidos)
            actual_hash = plan_sha256(plan)
            if expect_plan_sha256 and actual_hash != expect_plan_sha256:
                raise click.ClickException("PLAN_SHA256 no coincide; no se escribio ningun dato")
            result = execute_plan(plan, google, source_documents=source_documents)
            if report_path:
                write_json(report_path, result)
            click.echo(final_summary_text(result["summary"]))
