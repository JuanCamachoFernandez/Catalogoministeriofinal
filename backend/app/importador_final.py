import json
import os
import re
import secrets
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from pathlib import Path

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import Enum, Integer, Numeric, String, inspect as sa_inspect, select, text
from sqlalchemy.exc import DBAPIError
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
from .utilidades import bounded_slug, slugify

TOKEN_DEFAULT = "/secrets/google-import-token.json"
LOCK_KEY = 7420192601
ACCEPTED_NON_BLOCKING_WARNINGS = {
    "producto_incompleto_draft",
    "producto_general_ambiguo",
    "fotografias_generales_ambiguas",
}

SQLSTATE_REASONS = {
    "22001": "value too long for varchar",
    "22003": "numeric value out of range",
    "22P02": "invalid value for database type",
    "22P05": "unsupported Unicode sequence",
    "23502": "null in a NOT NULL column",
    "23503": "foreign key violation",
    "23505": "unique constraint violation",
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


def _source_context(row):
    return {
        "source": row.get("source", "UNKNOWN"),
        "worksheet": row.get("worksheet", "UNKNOWN"),
        "row": row.get("row_number"),
    }


def _unit_values(payload, logo=None):
    safe_phone = payload["phone"] if re.fullmatch(r"[67][0-9]{7}", payload.get("phone", "")) else ""
    safe_nit = payload.get("nit") if 5 <= len(payload.get("nit", "")) <= 12 else None
    return {
        "nombre_comercial": payload["business_name"], "razon_social": payload["legal_name"],
        "nit": safe_nit, "registro_seprec": payload.get("seprec") or None,
        "registro_pro_bolivia": payload.get("pro_bolivia") or None,
        "nombres_representante": payload["first_names"],
        "apellido_paterno_representante": payload["paternal_name"],
        "apellido_materno_representante": payload["maternal_name"],
        "departamento": payload["department"], "direccion_fisica": payload["address"],
        "telefono_whatsapp": safe_phone, "correo_electronico": payload["email"],
        "facebook_url": payload.get("facebook") or None, "instagram_url": payload.get("instagram") or None,
        "tiktok_url": payload.get("tiktok") or None, "resena_comercial": payload["review"],
        "logo_url": logo["url"] if logo else None,
        "logo_public_id": logo["public_id"] if logo else None,
    }


def _product_values(plan_product):
    complete = _product_complete(plan_product)
    return {
        "nombre": plan_product["name"], "slug": bounded_slug(plan_product["name"]),
        "descripcion": plan_product.get("description") or "",
        "nombre_comercial": plan_product["name"],
        "descripcion_tecnica": plan_product.get("description") or None,
        "materia_prima": plan_product.get("material") or None,
        "dimensiones": plan_product.get("dimensions") or None,
        "colores_disponibles": plan_product.get("colors") or None,
        "certificaciones": plan_product.get("certifications") or None,
        "presentacion": plan_product.get("presentation") or None,
        "presentacion_empaque": plan_product.get("presentation") or None,
        "precio_referencia": plan_product.get("price"), "precio": plan_product.get("price"),
        "capacidad_produccion_stock": plan_product.get("stock") or None,
        "estado": ProductStatus.AVAILABLE if complete else ProductStatus.DRAFT,
    }


def _preflight_issue(context, model, column, reason, **details):
    return {**context, "model": model.__name__, "table": model.__tablename__,
            "column": column.name, "reason": reason, **details}


def _validate_model_values(model, values, context, field_headers=None):
    issues = []
    field_headers = field_headers or {}
    for attribute in sa_inspect(model).column_attrs:
        key, column = attribute.key, attribute.columns[0]
        if key not in values:
            continue
        value = values[key]
        issue_context = {**context, "source_header": field_headers.get(key, "")}
        if value is None:
            if not column.nullable and column.default is None and column.server_default is None:
                issues.append(_preflight_issue(issue_context, model, column, "null_not_allowed"))
            continue
        column_type = column.type
        if isinstance(column_type, Enum):
            allowed = set(column_type.enums or [])
            candidate = value.name if hasattr(value, "name") else str(value)
            if candidate not in allowed:
                issues.append(_preflight_issue(issue_context, model, column, "invalid_enum"))
        elif isinstance(column_type, String):
            if not isinstance(value, str):
                issues.append(_preflight_issue(issue_context, model, column, "invalid_string_type"))
                continue
            if "\x00" in value:
                issues.append(_preflight_issue(issue_context, model, column, "nul_character_not_supported"))
            if column_type.length is not None and len(value) > column_type.length:
                issues.append(_preflight_issue(
                    issue_context, model, column, "value_too_long",
                    actual_length=len(value), max_length=column_type.length,
                ))
        elif isinstance(column_type, Numeric):
            try:
                number = Decimal(str(value))
            except (InvalidOperation, ValueError):
                issues.append(_preflight_issue(issue_context, model, column, "invalid_numeric"))
                continue
            integer_digits = max(1, len(str(abs(int(number)))))
            decimal_digits = max(0, -number.as_tuple().exponent)
            if (column_type.precision is not None and column_type.scale is not None
                    and (integer_digits > column_type.precision - column_type.scale
                         or decimal_digits > column_type.scale)):
                issues.append(_preflight_issue(
                    issue_context, model, column, "numeric_out_of_range",
                    precision=column_type.precision, scale=column_type.scale,
                ))
        elif isinstance(column_type, Integer) and (isinstance(value, bool) or not isinstance(value, int)):
            issues.append(_preflight_issue(issue_context, model, column, "invalid_integer"))
    return issues


def preflight_plan(plan):
    """Validate all deterministic database values before any write or image download."""
    issues = []
    run_context = {"source": "PLAN", "worksheet": "-", "row": None}
    issues.extend(_validate_model_values(FinalImportRun, {
        "plan_hash": plan.get("plan_hash"),
        "general_sheet_id": plan.get("sources", {}).get("general", {}).get("sheet_id"),
        "corrected_sheet_id": plan.get("sources", {}).get("corrected", {}).get("sheet_id"),
        "general_sheet_hash": plan.get("sources", {}).get("general", {}).get("hash"),
        "corrected_sheet_hash": plan.get("sources", {}).get("corrected", {}).get("hash"),
        "status": "RUNNING",
    }, run_context))
    for row in plan.get("trace_rows", []):
        context = _source_context(row)
        issues.extend(_validate_model_values(FinalImportSourceRow, {
            "source": row.get("source"), "sheet_id": row.get("sheet_id"),
            "worksheet": row.get("worksheet"), "row_number": row.get("row_number"),
            "row_hash": row.get("row_hash"), "source_data": row.get("data") or {},
            "warnings": row.get("warnings") or [], "is_ambiguous": bool(row.get("ambiguous")),
            "pending_reasons": row.get("pending_reasons") or [], "is_pending": bool(row.get("pending")),
        }, context))
        try:
            serialized = json.dumps(row.get("data") or {}, ensure_ascii=False)
            if "\\u0000" in serialized.lower():
                issues.append(_preflight_issue(context, FinalImportSourceRow,
                                               FinalImportSourceRow.__table__.c.datos_originales,
                                               "nul_character_not_supported"))
        except (TypeError, ValueError):
            issues.append(_preflight_issue(context, FinalImportSourceRow,
                                           FinalImportSourceRow.__table__.c.datos_originales,
                                           "invalid_json"))
    for group in plan.get("units", []):
        context = _source_context(group["rows"][0])
        common = _unit_values(group["unit"])
        unit_headers = group["unit"].get("_field_headers", {})
        issues.extend(_validate_model_values(RegistrationRequest, common, context, unit_headers))
        issues.extend(_validate_model_values(ProductiveUnit, common, context, unit_headers))
        user_headers = {
            "email": unit_headers.get("correo_electronico", ""),
            "first_name": unit_headers.get("nombres_representante", ""),
            "last_name": unit_headers.get("apellido_paterno_representante", ""),
            "apellido_paterno": unit_headers.get("apellido_paterno_representante", ""),
            "apellido_materno": unit_headers.get("apellido_materno_representante", ""),
            "phone": unit_headers.get("telefono_whatsapp", ""),
        }
        issues.extend(_validate_model_values(User, {
            "username": (slugify(group["unit"]["email"].split("@")[0])[:60] or "responsable"),
            "email": group["unit"]["email"], "first_name": group["unit"]["first_names"],
            "last_name": group["unit"]["paternal_name"],
            "apellido_paterno": group["unit"]["paternal_name"],
            "apellido_materno": group["unit"]["maternal_name"],
            "phone": common["telefono_whatsapp"] or None,
            "role": Role.PRODUCTIVE_UNIT_RESPONSIBLE, "status": UserStatus.ACTIVE,
            "must_change_password": True,
        }, context, user_headers))
        for product in group.get("products", []):
            product_context = _source_context(product["origin"])
            product_values = _product_values(product)
            issues.extend(_validate_model_values(
                Product, product_values, product_context, product["origin"].get("field_headers", {})
            ))
            issues.extend(_validate_model_values(FinalImportEntityTrace, {
                "entity_type": "PRODUCT", "entity_key": normalize(product["name"]),
            }, product_context))
            for drive_file_id in product.get("images", [])[:3]:
                issues.extend(_validate_model_values(FinalImportEntityTrace, {
                    "entity_type": "PRODUCT_IMAGE", "entity_key": "0" * 36,
                    "drive_file_id": drive_file_id,
                }, product_context))
    return issues


def preflight_summary_text(issues):
    lines = ["PRE-COMMIT VALIDATION"]
    if not issues:
        return "\n".join((lines[0], "- errors: 0"))
    for issue in issues:
        location = f"{issue['source']}/{issue['worksheet']}/fila {issue['row']}"
        details = ""
        if "actual_length" in issue:
            details = f" length={issue['actual_length']} max={issue['max_length']}"
        header = re.sub(r"\s+", " ", issue.get("source_header") or "").strip()
        header_detail = f" header={json.dumps(header, ensure_ascii=False)}" if header else ""
        lines.append(f"- {location}: {issue['table']}.{issue['column']} "
                     f"{issue['reason']}{details}{header_detail}")
    lines.append(f"- errors: {len(issues)}")
    return "\n".join(lines)


def _raise_runtime_validation(issues):
    if issues:
        raise click.ClickException(
            f"La validacion previa a escritura detecto {len(issues)} valores incompatibles\n"
            + preflight_summary_text(issues)
        )


def _flush_with_context(model, context):
    try:
        db.session.flush()
    except Exception as exc:
        exc._final_import_context = {**context, "model": model.__name__, "table": model.__tablename__}
        raise


def _safe_identifier(value):
    value = str(value or "")
    return value if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value) else None


def safe_database_error(exc):
    context = getattr(exc, "_final_import_context", {})
    original = exc.orig if isinstance(exc, DBAPIError) else getattr(exc, "orig", None)
    diagnostic = getattr(original, "diag", None)
    sqlstate = getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)
    table = _safe_identifier(getattr(diagnostic, "table_name", None)) or context.get("table") or "unknown"
    column = _safe_identifier(getattr(diagnostic, "column_name", None)) or "unknown"
    reason = SQLSTATE_REASONS.get(sqlstate, "database rejected a value")
    payload = {
        "exception_type": type(exc).__name__, "table": table, "column": column,
        "sqlstate": sqlstate or "unknown", "reason": reason,
        "model": context.get("model", "unknown"), "source": context.get("source", "unknown"),
        "worksheet": context.get("worksheet", "unknown"), "row": context.get("row"),
    }
    current_app.logger.error("final_import_database_error=%s", json.dumps(payload, sort_keys=True))
    return (
        f"tipo={payload['exception_type']} tabla={table} columna={column} "
        f"sqlstate={payload['sqlstate']} motivo={reason} modelo={payload['model']} "
        f"fuente={payload['source']} hoja={payload['worksheet']} fila={payload['row']}"
    )


def compensate_cloudinary(uploaded):
    deleted = failed = 0
    for public_id in reversed(uploaded):
        try:
            result = delete_cloudinary_upload(public_id)
            if isinstance(result, dict) and result.get("result") not in {"ok", "not found"}:
                failed += 1
            else:
                deleted += 1
        except Exception:
            failed += 1
    current_app.logger.info(
        "final_import_cloudinary_compensation attempted=%s deleted=%s failed=%s",
        len(uploaded), deleted, failed,
    )
    return {"attempted": len(uploaded), "deleted": deleted, "failed": failed}


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
        _flush_with_context(FinalImportSourceRow, _source_context(row))
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
        _flush_with_context(FinalImportEntityTrace, _source_context(row))
    for product, plan_product, images in product_entities:
        origin = plan_product["origin"]
        source_row = row_models[(origin["source"], origin["worksheet"], origin["row_number"])]
        db.session.add(FinalImportEntityTrace(source_row_id=source_row.id, entity_type="PRODUCT",
                                             entity_id=product.id, entity_key=normalize(product.nombre)))
        _flush_with_context(FinalImportEntityTrace, _source_context(origin))
        for image, drive_file_id in images:
            db.session.add(FinalImportEntityTrace(source_row_id=source_row.id, entity_type="PRODUCT_IMAGE",
                entity_id=image.id, entity_key=str(image.id), drive_file_id=drive_file_id))
            _flush_with_context(FinalImportEntityTrace, _source_context(origin))


def import_unit(group, google, row_models, uploaded, counters):
    payload = group["unit"]
    unit = existing_unit(payload)
    if not unit:
            logo = None
            if payload.get("logo_drive_id"):
                filename, stream = google.download(payload["logo_drive_id"])
                logo = upload_to_cloudinary(FileStorage(stream=stream, filename=filename), "logos", "unit_logo")
                if logo and logo.get("public_id"): uploaded.append(logo["public_id"])
                context = _source_context(group["rows"][0])
                unit_headers = payload.get("_field_headers", {})
                _raise_runtime_validation(
                    _validate_model_values(RegistrationRequest, _unit_values(payload, logo), context, unit_headers)
                    + _validate_model_values(ProductiveUnit, _unit_values(payload, logo), context, unit_headers)
                )
            user = User(username=unique_username(payload["email"]), email=payload["email"], role=Role.PRODUCTIVE_UNIT_RESPONSIBLE,
                first_name=payload["first_names"], last_name=payload["paternal_name"], apellido_paterno=payload["paternal_name"],
                apellido_materno=payload["maternal_name"], phone=_unit_values(payload)["telefono_whatsapp"] or None,
                status=UserStatus.ACTIVE,
                must_change_password=True)
            user.set_password(secrets.token_urlsafe(32))
            db.session.add(user)
            _flush_with_context(User, _source_context(group["rows"][0]))
            counters["users_created"] += 1
            common = _unit_values(payload, logo)
            request_item = RegistrationRequest(**common, estado=RegistrationStatus.APPROVED, fecha_revision=datetime.now(timezone.utc))
            db.session.add(request_item)
            _flush_with_context(RegistrationRequest, _source_context(group["rows"][0]))
            unit = ProductiveUnit(**common, user_id=user.id, registration_request_id=request_item.id,
                                  estado=ProductiveUnitStatus.ACTIVE, fecha_aprobacion=datetime.now(timezone.utc))
            db.session.add(unit)
            _flush_with_context(ProductiveUnit, _source_context(group["rows"][0]))
            counters["units_created"] += 1
            if logo:
                counters["logos_uploaded"] += 1
            for sector_name in payload.get("sectors", []):
                sector = db.session.scalar(select(ProductiveSector).where(ProductiveSector.nombre.ilike(sector_name)))
                if sector:
                    db.session.add(UnitSector(productive_unit_id=unit.id, productive_sector_id=sector.id, estado=SectorStatus.ACTIVE))
                    _flush_with_context(UnitSector, _source_context(group["rows"][0]))
                    counters["sectors_associated"] += 1
    known = {normalize(name) for name in db.session.scalars(select(Product.nombre).where(Product.productive_unit_id == unit.id)).all()}
    entities = []
    for plan_product in group["products"]:
            key = normalize(plan_product["name"])
            if key in known or len(known) >= MAX_PRODUCTS: continue
            complete = _product_complete(plan_product)
            product = Product(productive_unit_id=unit.id, **_product_values(plan_product))
            db.session.add(product)
            _flush_with_context(Product, _source_context(plan_product["origin"]))
            counters["products_created"] += 1
            if not complete:
                counters["products_draft"] += 1
            images = []
            for order, drive_file_id in enumerate(plan_product.get("images", [])[:3]):
                filename, stream = google.download(drive_file_id)
                result = upload_to_cloudinary(FileStorage(stream=stream, filename=filename), "productos", "product")
                if result.get("public_id"): uploaded.append(result["public_id"])
                image_values = {
                    "filename": result.get("filename"), "url": result.get("url"),
                    "public_id": result.get("public_id"), "alt_text": product.nombre,
                    "is_cover": order == 0, "display_order": order,
                }
                _raise_runtime_validation(_validate_model_values(
                    ProductImage, image_values, _source_context(plan_product["origin"])
                ))
                image = ProductImage(product_id=product.id, filename=result["filename"], url=result["url"],
                    public_id=result.get("public_id"), alt_text=product.nombre, is_cover=order == 0, display_order=order)
                db.session.add(image)
                _flush_with_context(ProductImage, _source_context(plan_product["origin"]))
                images.append((image, drive_file_id))
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
    preflight_issues = preflight_plan(plan)
    if preflight_issues:
        raise click.ClickException(
            f"El preflight detecto {len(preflight_issues)} valores incompatibles; no se escribio ningun dato\n"
            + preflight_summary_text(preflight_issues)
        )
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
        db.session.add(run)
        _flush_with_context(FinalImportRun, {"source": "PLAN", "worksheet": "-", "row": None})
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
        run.finished_at = datetime.now(timezone.utc)
        _flush_with_context(FinalImportRun, {"source": "PLAN", "worksheet": "-", "row": None})
        db.session.commit()
        return {"plan_hash": plan["plan_hash"], "status": run.status, "summary": counters}
    except Exception as exc:
        db.session.rollback()
        cleanup = compensate_cloudinary(uploaded)
        if isinstance(exc, click.ClickException):
            raise click.ClickException(
                f"{exc.format_message()}; cloudinary_compensation="
                f"{cleanup['deleted']}/{cleanup['attempted']} failed={cleanup['failed']}"
            ) from exc
        if isinstance(exc, DBAPIError):
            detail = safe_database_error(exc)
        else:
            detail = f"tipo={type(exc).__name__} motivo=operation failed"
            current_app.logger.error("final_import_error type=%s", type(exc).__name__)
        raise click.ClickException(
            f"La importacion fue revertida: {detail}; "
            f"cloudinary_compensation={cleanup['deleted']}/{cleanup['attempted']} failed={cleanup['failed']}"
        ) from exc
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
            click.echo(preflight_summary_text(preflight_plan(plan)))
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
