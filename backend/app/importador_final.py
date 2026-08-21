import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

import click
from flask.cli import with_appcontext
from sqlalchemy import select, text
from werkzeug.datastructures import FileStorage

from .extensiones import db
from .fuentes_importacion import GoogleSource, MAX_PRODUCTS, build_plan, normalize, sha
from .modelos import (
    FinalImportEntityTrace, FinalImportRun, FinalImportSourceRow, Product, ProductImage,
    ProductStatus, ProductiveSector, ProductiveUnit, ProductiveUnitStatus,
    RegistrationRequest, RegistrationStatus, Role, SectorStatus, UnitSector, User, UserStatus,
)
from .servicios import delete_cloudinary_upload, upload_to_cloudinary
from .utilidades import slugify

TOKEN_DEFAULT = "/secrets/google-import-token.json"
LOCK_KEY = 7420192601


def write_json(path, payload):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)


def dry_run_summary_text(summary):
    """Render only aggregate counters; never echo source values or identifiers."""
    lines = ["ERRORS BY REASON"]
    reasons = summary.get("errors_by_reason") or {}
    if reasons:
        lines.extend(f"- {reason}: {count}" for reason, count in sorted(reasons.items()))
    else:
        lines.append("- none: 0")
    for label, key in (("GENERAL", "general"), ("CORREGIDOS", "corrected")):
        source = (summary.get("sources") or {}).get(key, {})
        lines.extend((
            "", f"{label}:",
            f"- filas leídas: {source.get('rows_read', 0)}",
            f"- válidas: {source.get('valid', 0)}",
            f"- inválidas: {source.get('invalid', 0)}",
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


def trace_entities(run, group, unit, product_entities):
    row_models = {}
    for row in group["rows"]:
        source_row = FinalImportSourceRow(run_id=run.id, source=row["source"], sheet_id=row["sheet_id"],
            worksheet=row["worksheet"], row_number=row["row_number"], row_hash=row["row_hash"], productive_unit_id=unit.id)
        db.session.add(source_row); db.session.flush()
        row_models[(row["source"], row["worksheet"], row["row_number"])] = source_row
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


def import_unit(run, group, google):
    payload, uploaded = group["unit"], []
    try:
        unit = existing_unit(payload)
        if not unit:
            logo = None
            if payload.get("logo_drive_id"):
                filename, stream = google.download(payload["logo_drive_id"])
                logo = upload_to_cloudinary(FileStorage(stream=stream, filename=filename), "logos", "unit_logo")
                if logo and logo.get("public_id"): uploaded.append(logo["public_id"])
            user = User(username=unique_username(payload["email"]), email=payload["email"], role=Role.PRODUCTIVE_UNIT_RESPONSIBLE,
                first_name=payload["first_names"], last_name=payload["paternal_name"], apellido_paterno=payload["paternal_name"],
                apellido_materno=payload["maternal_name"], phone=payload["phone"][:15], status=UserStatus.ACTIVE,
                must_change_password=True)
            user.set_password(secrets.token_urlsafe(32))
            db.session.add(user)
            common = dict(nombre_comercial=payload["business_name"], razon_social=payload["legal_name"], nit=payload.get("nit") or None,
                registro_seprec=payload.get("seprec") or None, registro_pro_bolivia=payload.get("pro_bolivia") or None,
                nombres_representante=payload["first_names"], apellido_paterno_representante=payload["paternal_name"],
                apellido_materno_representante=payload["maternal_name"], departamento=payload["department"],
                direccion_fisica=payload["address"], telefono_whatsapp=payload["phone"], correo_electronico=payload["email"],
                facebook_url=payload.get("facebook") or None, instagram_url=payload.get("instagram") or None,
                tiktok_url=payload.get("tiktok") or None, resena_comercial=payload["review"],
                logo_url=logo["url"] if logo else None, logo_public_id=logo["public_id"] if logo else None)
            request_item = RegistrationRequest(**common, estado=RegistrationStatus.APPROVED, fecha_revision=datetime.now(timezone.utc))
            db.session.add(request_item); db.session.flush()
            unit = ProductiveUnit(**common, user_id=user.id, registration_request_id=request_item.id,
                                  estado=ProductiveUnitStatus.ACTIVE, fecha_aprobacion=datetime.now(timezone.utc))
            db.session.add(unit); db.session.flush()
            for sector_name in payload.get("sectors", []):
                sector = db.session.scalar(select(ProductiveSector).where(ProductiveSector.nombre.ilike(sector_name)))
                if sector:
                    db.session.add(UnitSector(productive_unit_id=unit.id, productive_sector_id=sector.id, estado=SectorStatus.ACTIVE))
        known = {normalize(name) for name in db.session.scalars(select(Product.nombre).where(Product.productive_unit_id == unit.id)).all()}
        entities = []
        for plan_product in group["products"]:
            key = normalize(plan_product["name"])
            if key in known or len(known) >= MAX_PRODUCTS: continue
            complete = bool(plan_product.get("description") and plan_product.get("images"))
            product = Product(productive_unit_id=unit.id, nombre=plan_product["name"], slug=slugify(plan_product["name"]),
                descripcion=plan_product.get("description") or "", nombre_comercial=plan_product["name"],
                descripcion_tecnica=plan_product.get("description") or None,
                estado=ProductStatus.AVAILABLE if complete else ProductStatus.DRAFT)
            db.session.add(product); db.session.flush()
            images = []
            for order, drive_file_id in enumerate(plan_product.get("images", [])[:3]):
                filename, stream = google.download(drive_file_id)
                result = upload_to_cloudinary(FileStorage(stream=stream, filename=filename), "productos", "product")
                if result.get("public_id"): uploaded.append(result["public_id"])
                image = ProductImage(product_id=product.id, filename=result["filename"], url=result["url"],
                    public_id=result.get("public_id"), alt_text=product.nombre, is_cover=order == 0, display_order=order)
                db.session.add(image); db.session.flush(); images.append((image, drive_file_id))
            entities.append((product, plan_product, images)); known.add(key)
        trace_entities(run, group, unit, entities)
        db.session.commit()
        return {"unit": payload["business_name"], "status": "IMPORTED", "products": len(entities)}
    except Exception as exc:
        db.session.rollback()
        for public_id in reversed(uploaded):
            try: delete_cloudinary_upload(public_id)
            except Exception: pass
        return {"unit": payload.get("business_name"), "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"[:500]}


def execute_plan(plan, google):
    if sha({k: v for k, v in plan.items() if k != "plan_hash"}) != plan.get("plan_hash"):
        raise click.ClickException("El archivo de plan fue alterado o está incompleto")
    general = google.spreadsheet(plan["sources"]["general"]["sheet_id"])
    corrected = google.spreadsheet(plan["sources"]["corrected"]["sheet_id"])
    if sha(general) != plan["sources"]["general"]["hash"] or sha(corrected) != plan["sources"]["corrected"]["hash"]:
        raise click.ClickException("Una hoja cambió después del dry-run; genere un plan nuevo")
    if db.session.scalar(select(FinalImportRun.id).where(FinalImportRun.plan_hash == plan["plan_hash"])):
        raise click.ClickException("Este plan ya fue ejecutado; no se repetirá")
    postgres = db.engine.dialect.name == "postgresql"
    if postgres and not db.session.scalar(select(db.func.pg_try_advisory_lock(LOCK_KEY))):
        raise click.ClickException("Ya existe otra importación final en ejecución")
    try:
        run = FinalImportRun(plan_hash=plan["plan_hash"], general_sheet_id=plan["sources"]["general"]["sheet_id"],
            corrected_sheet_id=plan["sources"]["corrected"]["sheet_id"], general_sheet_hash=plan["sources"]["general"]["hash"],
            corrected_sheet_hash=plan["sources"]["corrected"]["hash"], status="RUNNING")
        db.session.add(run); db.session.commit()
        results = [import_unit(run, group, google) for group in plan["units"]]
        run = db.session.get(FinalImportRun, run.id)
        run.status = "COMPLETED_WITH_ERRORS" if any(x["status"] == "ERROR" for x in results) else "COMPLETED"
        run.summary = {"units": len(results), "imported": sum(x["status"] == "IMPORTED" for x in results),
                       "errors": sum(x["status"] == "ERROR" for x in results)}
        run.finished_at = datetime.now(timezone.utc); db.session.commit()
        return {"plan_hash": plan["plan_hash"], "status": run.status, "summary": run.summary, "units": results}
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
    @click.option("--report", "report_path", required=True, type=click.Path(dir_okay=False))
    @click.option("--token", "token_path", default=lambda: os.getenv("GOOGLE_IMPORT_TOKEN_PATH", TOKEN_DEFAULT), show_default=True)
    @with_appcontext
    def importar_datos_finales(sheet_general, sheet_corregidos, dry_run, do_commit, plan_path, report_path, token_path):
        if dry_run == do_commit: raise click.ClickException("Seleccione exactamente uno: --dry-run o --commit")
        google = GoogleSource(token_path)
        if dry_run:
            if not sheet_general or not sheet_corregidos:
                raise click.ClickException("--sheet-general y --sheet-corregidos son obligatorios en dry-run")
            plan = build_plan(google.spreadsheet(sheet_general), google.spreadsheet(sheet_corregidos), sheet_general, sheet_corregidos)
            write_json(report_path, plan)
            click.echo(dry_run_summary_text(plan["summary"]))
            click.echo(f"Plan guardado en {report_path}. No se escribió PostgreSQL ni Cloudinary.")
        else:
            if not plan_path: raise click.ClickException("--plan es obligatorio con --commit")
            result = execute_plan(json.loads(Path(plan_path).read_text(encoding="utf-8")), google)
            write_json(report_path, result); click.echo(json.dumps(result["summary"], ensure_ascii=False, indent=2))
            if result["status"] != "COMPLETED":
                raise click.ClickException("La importación terminó con errores por unidad; revise el reporte")
