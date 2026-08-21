import hashlib
import io
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import click

SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
)
MAX_PRODUCTS = 15
MAX_IMAGES = 3

ALIASES = {
    "business_name": (
        "nombre comercial", "nombre de la unidad productiva", "unidad productiva",
        "emprendimiento", "nombre del emprendimiento", "nombre de la empresa",
    ),
    "legal_name": ("razon social", "razón social", "nombre o razon social", "nombre o razón social"),
    "nit": ("nit", "numero de nit", "número de nit"),
    "email": ("correo electronico", "correo electrónico", "email", "correo", "e mail"),
    "phone": (
        "telefono whatsapp", "teléfono whatsapp", "numero de whatsapp", "número de whatsapp",
        "celular whatsapp", "celular", "telefono", "teléfono",
    ),
    "first_names": ("nombres representante", "nombres del representante", "nombres del responsable", "nombre responsable"),
    "paternal_name": ("apellido paterno representante", "apellido paterno"),
    "maternal_name": ("apellido materno representante", "apellido materno"),
    "representative_name": (
        "nombre completo del representante", "nombre del representante legal",
        "nombre completo del responsable", "nombre y apellidos del representante",
        "representante legal", "representante", "propietario",
    ),
    "department": ("departamento",),
    "address": ("direccion fisica", "dirección física", "direccion", "dirección"),
    "review": ("resena comercial", "reseña comercial", "descripcion del emprendimiento", "descripción del emprendimiento"),
    "sectors": ("sectores", "sector productivo", "rubros"),
    "logo": ("logo", "logotipo", "logo drive", "id logo"),
    "products": ("productos", "productos que elabora", "descripcion de productos", "descripción de productos"),
    "facebook": ("facebook",), "instagram": ("instagram",), "tiktok": ("tiktok",),
    "seprec": ("registro seprec", "seprec"), "pro_bolivia": ("registro pro bolivia", "pro bolivia"),
}

REQUIRED_UNIT_FIELDS = (
    "business_name", "legal_name", "email", "phone", "first_names", "paternal_name",
    "maternal_name", "department", "address", "review",
)
CORE_HEADER_FIELDS = ("business_name", "email", "phone", "representative_name", "first_names")
DEPARTMENTS = {
    "beni": "Beni", "chuquisaca": "Chuquisaca", "cochabamba": "Cochabamba",
    "la paz": "La Paz", "oruro": "Oruro", "pando": "Pando", "potosi": "Potosí",
    "santa cruz": "Santa Cruz", "tarija": "Tarija",
}


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c)).lower().strip()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()


NORMALIZED_ALIASES = {key: tuple(normalize(v) for v in values) for key, values in ALIASES.items()}


def sha(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _header_score(header, alias):
    if header == alias:
        return 1000 + len(alias)
    if len(alias) >= 5 and f" {alias} " in f" {header} ":
        return len(alias)
    return 0


def _field_header(row, name):
    candidates = []
    for header in row:
        normalized_header = normalize(header)
        if name == "business_name" and "producto" in normalized_header:
            continue
        score = max((_header_score(normalized_header, alias) for alias in NORMALIZED_ALIASES[name]), default=0)
        if score:
            candidates.append((score, str(header)))
    return max(candidates, default=(0, ""))[1]


def field(row, name):
    header = _field_header(row, name)
    return str(row.get(header) or "").strip() if header else ""


def drive_id(value):
    value = str(value or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{20,}", value):
        return value
    match = re.search(r"(?:/d/|[?&]id=)([A-Za-z0-9_-]{20,})", value)
    return match.group(1) if match else None


def clear_items(value):
    """Only split explicit semicolon/newline/numbered enumerations; never commas."""
    value = str(value or "").strip()
    if not value:
        return []
    if ";" in value or "\n" in value:
        return [x.strip(" -\t") for x in re.split(r"[;\n]+", value) if x.strip(" -\t")]
    numbered = re.split(r"(?:^|\s)(?:\d{1,2}[.)-])\s*", value)
    return [x.strip() for x in numbered if x.strip()] if len(numbered) > 2 else []


def sector_items(value):
    value = str(value or "").strip()
    if not value:
        return []
    return clear_items(value) or [value]


class GoogleSource:
    def __init__(self, token_path):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ModuleNotFoundError as exc:
            raise click.ClickException("Faltan dependencias Google API") from exc
        if not Path(token_path).is_file():
            raise click.ClickException(f"No existe el token de importación: {token_path}")
        credentials = Credentials.from_authorized_user_file(token_path, SCOPES)
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        if not credentials.valid:
            raise click.ClickException("El token Google de importación no es válido")
        self.sheets = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        self.drive = build("drive", "v3", credentials=credentials, cache_discovery=False)

    def spreadsheet(self, sheet_id):
        metadata = self.sheets.spreadsheets().get(
            spreadsheetId=sheet_id, fields="properties.title,sheets.properties(title,index)"
        ).execute()
        result = {"title": metadata.get("properties", {}).get("title", ""), "worksheets": []}
        for item in sorted(metadata.get("sheets", []), key=lambda x: x["properties"].get("index", 0)):
            title = item["properties"]["title"]
            values = self.sheets.spreadsheets().values().get(
                spreadsheetId=sheet_id, range=f"'{title.replace(chr(39), chr(39) * 2)}'"
            ).execute().get("values", [])
            result["worksheets"].append({"title": title, "values": values})
        return result

    def download(self, file_id):
        from googleapiclient.http import MediaIoBaseDownload
        metadata = self.drive.files().get(fileId=file_id, fields="id,name,mimeType,size", supportsAllDrives=True).execute()
        if str(metadata.get("mimeType", "")).startswith("application/vnd.google-apps"):
            raise ValueError("El archivo Drive no es una imagen binaria")
        output = io.BytesIO()
        downloader = MediaIoBaseDownload(output, self.drive.files().get_media(fileId=file_id, supportsAllDrives=True))
        done = False
        while not done:
            _status, done = downloader.next_chunk()
        output.seek(0)
        return metadata.get("name") or f"{file_id}.jpg", output


def _recognized_fields(headers):
    empty_row = {str(header): "" for header in headers}
    return [name for name in ALIASES if _field_header(empty_row, name)]


def _header_row(values):
    """Find the header row instead of assuming that it is always row one."""
    candidates = []
    for index, values_row in enumerate(values[:20]):
        headers = [str(value).strip() for value in values_row]
        recognized = _recognized_fields(headers)
        candidates.append((len(recognized), len([header for header in headers if header]), -index, index, headers, recognized))
    if not candidates:
        return None, [], []
    _score, _width, _position, index, headers, recognized = max(candidates)
    return index, headers, recognized


def _worksheet_dicts(worksheet):
    values = worksheet.get("values") or []
    if not values:
        return [], {"header_row": None, "recognized_fields": [], "header_found": False, "rows_read": 0}
    header_index, headers, recognized = _header_row(values)
    if header_index is None:
        return [], {"header_row": None, "recognized_fields": [], "header_found": False, "rows_read": 0}
    result = []
    for offset, values_row in enumerate(values[header_index + 1:], header_index + 2):
        row = {header: values_row[index] if index < len(values_row) else "" for index, header in enumerate(headers) if header}
        if any(str(value).strip() for value in row.values()):
            result.append((offset, row))
    metadata = {
        "header_row": header_index + 1,
        "recognized_fields": recognized,
        "header_found": any(name in recognized for name in CORE_HEADER_FIELDS),
        "rows_read": len(result),
    }
    return result, metadata


def _source_rows(document, source, sheet_id, worksheets=None):
    result, diagnostics = [], []
    selected = worksheets if worksheets is not None else document.get("worksheets", [])
    for worksheet in selected:
        worksheet_rows, metadata = _worksheet_dicts(worksheet)
        diagnostics.append({"worksheet": worksheet.get("title", ""), **metadata})
        for number, row in worksheet_rows:
            result.append({
                "source": source, "sheet_id": sheet_id, "worksheet": worksheet.get("title", ""),
                "row_number": number, "row_hash": sha(row), "data": row,
                "header_found": metadata["header_found"],
            })
    return result, diagnostics


def rows(document, source, sheet_id):
    result, _diagnostics = _source_rows(document, source, sheet_id)
    return result


def _any_field(row, names):
    for name in names:
        candidates = []
        for key, value in row.items():
            score = _header_score(normalize(key), normalize(name))
            if score and str(value or "").strip():
                candidates.append((score, str(value).strip()))
        if candidates:
            return max(candidates)[1]
    return ""


def _corrected_rows(document, sheet_id):
    """Flatten the prior relational template (units/sectors/products/images) when present."""
    worksheets = {normalize(item["title"]): item for item in document["worksheets"]}
    units_sheet = next((item for title, item in worksheets.items() if "unidad" in title), None)
    products_sheet = next((item for title, item in worksheets.items() if "producto" in title and "imagen" not in title), None)
    sector_sheet = next((item for title, item in worksheets.items() if "sector" in title), None)
    image_sheet = next((item for title, item in worksheets.items() if "imagen" in title or "foto" in title), None)
    relational = bool(units_sheet or products_sheet or sector_sheet or image_sheet)
    if not relational:
        return _source_rows(document, "CORRECTED", sheet_id)
    if not units_sheet:
        diagnostics = [{"worksheet": "Unidades", "header_row": None, "recognized_fields": [],
                        "header_found": False, "rows_read": 0, "missing_worksheet": True}]
        return [], diagnostics
    unit_rows, unit_metadata = _worksheet_dicts(units_sheet)
    product_rows, product_metadata = _worksheet_dicts(products_sheet or {})
    sectors, sector_metadata = _worksheet_dicts(sector_sheet or {})
    images, image_metadata = _worksheet_dicts(image_sheet or {})
    unit_ref_names = (
        "id unidad", "id_unidad", "codigo unidad", "código unidad", "codigo_unidad",
        "unidad id", "unidad_productiva_id", "nombre comercial", "unidad productiva",
    )
    product_ref_names = (
        "id producto", "id_producto", "codigo producto", "código producto", "codigo_producto",
        "producto id", "producto_id", "nombre producto", "producto",
    )
    result = []
    for number, unit_row in unit_rows:
        unit_ref = normalize(_any_field(unit_row, unit_ref_names) or field(unit_row, "business_name"))
        related_products = [row for _row_number, row in product_rows if normalize(_any_field(row, unit_ref_names)) == unit_ref]
        related_sectors = [row for _row_number, row in sectors if normalize(_any_field(row, unit_ref_names)) == unit_ref]
        enriched = dict(unit_row)
        sector_names = [_any_field(row, ("sector", "sector productivo", "nombre sector")) for row in related_sectors]
        if sector_names:
            enriched["Sectores"] = "; ".join(name for name in sector_names if name)
        for product_number, product_row in enumerate(related_products[:MAX_PRODUCTS], 1):
            product_ref = normalize(_any_field(product_row, product_ref_names))
            enriched[f"Producto {product_number}"] = _any_field(product_row, ("nombre producto", "producto", "nombre comercial"))
            enriched[f"Producto {product_number} descripcion"] = _any_field(
                product_row, ("descripcion", "descripción", "descripcion tecnica", "descripción técnica")
            )
            related_images = [row for _row_number, row in images if normalize(_any_field(row, product_ref_names)) == product_ref]
            for image_number, image_row in enumerate(related_images[:MAX_IMAGES], 1):
                enriched[f"Producto {product_number} imagen {image_number}"] = _any_field(
                    image_row, ("drive id", "id drive", "archivo drive", "imagen", "foto", "url")
                )
        result.append({"source": "CORRECTED", "sheet_id": sheet_id, "worksheet": units_sheet["title"],
                       "row_number": number, "row_hash": sha(enriched), "data": enriched,
                       "header_found": unit_metadata["header_found"]})
    diagnostics = [
        {"worksheet": units_sheet["title"], **unit_metadata},
        {"worksheet": (sector_sheet or {}).get("title", "Sectores"), **sector_metadata,
         "missing_worksheet": not bool(sector_sheet)},
        {"worksheet": (products_sheet or {}).get("title", "Productos"), **product_metadata,
         "missing_worksheet": not bool(products_sheet)},
        {"worksheet": (image_sheet or {}).get("title", "Imagenes"), **image_metadata,
         "missing_worksheet": not bool(image_sheet)},
    ]
    return result, diagnostics


def corrected_rows(document, sheet_id):
    result, _diagnostics = _corrected_rows(document, sheet_id)
    return result


def row_products(source_row):
    row = source_row["data"]
    normalized = {normalize(k): str(v or "").strip() for k, v in row.items()}
    products = []
    for number in range(1, MAX_PRODUCTS + 1):
        name = next((normalized.get(k) for k in (f"producto {number}", f"producto {number} nombre", f"nombre producto {number}") if normalized.get(k)), "")
        if not name:
            continue
        description = next((normalized.get(k) for k in (f"producto {number} descripcion", f"descripcion producto {number}") if normalized.get(k)), "")
        images = []
        for image_number in range(1, MAX_IMAGES + 1):
            value = next((normalized.get(k) for k in (f"producto {number} imagen {image_number}", f"imagen producto {number} {image_number}", f"foto producto {number} {image_number}") if normalized.get(k)), "")
            if drive_id(value):
                images.append(drive_id(value))
        products.append({"name": name, "description": description, "images": images,
                         "origin": {k: source_row[k] for k in ("source", "sheet_id", "worksheet", "row_number", "row_hash")}})
    raw = field(row, "products")
    if not products and raw:
        clear = clear_items(raw)
        if not clear:
            if "," in raw:
                return [], raw
            clear = [raw]
        products = [{"name": name, "description": "", "images": [],
                     "origin": {k: source_row[k] for k in ("source", "sheet_id", "worksheet", "row_number", "row_hash")}}
                    for name in clear[:MAX_PRODUCTS]]
    return products, None


def _split_representative(row, first_names, paternal_name, maternal_name):
    if first_names and paternal_name and maternal_name:
        return first_names, paternal_name, maternal_name, None
    full_name = field(row, "representative_name")
    if not full_name:
        return first_names, paternal_name, maternal_name, None
    parts = [part for part in re.split(r"\s+", full_name.strip()) if part]
    if len(parts) < 3:
        return first_names, paternal_name, maternal_name, "representante_no_divisible"
    return " ".join(parts[:-2]), parts[-2], parts[-1], None


def _canonical_phone(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 11 and digits.startswith("591"):
        digits = digits[3:]
    elif len(digits) == 9 and digits.startswith("0"):
        digits = digits[1:]
    return digits


def unit_payload(source_row):
    row = source_row["data"]
    first_names, paternal_name, maternal_name, representative_error = _split_representative(
        row, field(row, "first_names"), field(row, "paternal_name"), field(row, "maternal_name")
    )
    department_raw = field(row, "department")
    payload = {
        "business_name": field(row, "business_name"), "legal_name": field(row, "legal_name"),
        "nit": re.sub(r"\D", "", field(row, "nit")), "email": field(row, "email").lower(),
        "phone": _canonical_phone(field(row, "phone")), "first_names": first_names,
        "paternal_name": paternal_name, "maternal_name": maternal_name,
        "department": DEPARTMENTS.get(normalize(department_raw), department_raw),
        "address": field(row, "address"), "review": field(row, "review"),
        "facebook": field(row, "facebook"), "instagram": field(row, "instagram"), "tiktok": field(row, "tiktok"),
        "seprec": field(row, "seprec"), "pro_bolivia": field(row, "pro_bolivia"),
        "sectors": sector_items(field(row, "sectors")), "logo_drive_id": drive_id(field(row, "logo")),
    }
    return payload, representative_error


def _validation_reasons(group):
    unit = group["unit"]
    if any(not row.get("header_found", True) for row in group["rows"]):
        return [{"reason": "encabezado_no_encontrado"}]
    reasons = []
    missing = [key for key in REQUIRED_UNIT_FIELDS if not unit.get(key)]
    representative_missing = {"first_names", "paternal_name", "maternal_name"}.intersection(missing)
    if representative_missing:
        reasons.append({"reason": "representante_no_divisible"})
        missing = [key for key in missing if key not in representative_missing]
    if missing:
        reasons.append({"reason": "campo_obligatorio_faltante", "fields": missing})
    if unit.get("email") and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", unit["email"]):
        reasons.append({"reason": "correo_invalido"})
    if unit.get("phone") and not re.fullmatch(r"[67][0-9]{7}", unit["phone"]):
        reasons.append({"reason": "telefono_invalido"})
    if unit.get("department") and normalize(unit["department"]) not in DEPARTMENTS:
        reasons.append({"reason": "departamento_invalido"})
    if unit.get("nit") and not 5 <= len(unit["nit"]) <= 12:
        reasons.append({"reason": "nit_invalido"})
    return reasons


def _row_key(row):
    return row["source"], row["worksheet"], row["row_number"]


def build_plan(general_document, corrected_document, general_id, corrected_id):
    corrected_source_rows, corrected_diagnostics = _corrected_rows(corrected_document, corrected_id)
    general_source_rows, general_diagnostics = _source_rows(general_document, "GENERAL", general_id)
    source_rows = corrected_source_rows + general_source_rows
    groups, indexes = [], {"nit": {}, "email": {}, "email_phone": {}, "name": {}}
    conflicts, invalid, ambiguous, merged = [], [], [], 0
    for source_row in source_rows:
        (unit, representative_error), (products, unclear) = unit_payload(source_row), row_products(source_row)
        if unclear:
            ambiguous.append({"row": source_row["row_number"], "worksheet": source_row["worksheet"], "value": unclear})
        keys = []
        if len(unit["nit"]) >= 5: keys.append(("nit", unit["nit"]))
        if unit["email"]:
            keys.append(("email", unit["email"]))
            if unit["phone"]: keys.append(("email_phone", f'{unit["email"]}|{unit["phone"]}'))
        if unit["business_name"]: keys.append(("name", normalize(unit["business_name"])))
        matches = {indexes[k][v] for k, v in keys if v in indexes[k]}
        if len(matches) > 1:
            conflicts.append({"row": source_row["row_number"], "worksheet": source_row["worksheet"], "matches": sorted(matches)})
            continue
        if matches:
            index, merged = matches.pop(), merged + 1
            group = groups[index]
            contradictory = (
                len(unit["nit"]) >= 5 and len(group["unit"].get("nit", "")) >= 5
                and unit["nit"] != group["unit"]["nit"]
            ) or (
                unit["email"] and group["unit"].get("email")
                and unit["email"] != group["unit"]["email"]
            )
            if contradictory:
                conflicts.append({"row": source_row["row_number"], "worksheet": source_row["worksheet"],
                                  "matches": [index], "reason": "identificadores contradictorios"})
                merged -= 1
                continue
            if source_row["source"] == "CORRECTED": group["unit"].update({k: v for k, v in unit.items() if v})
            else:
                for key, value in unit.items():
                    if not group["unit"].get(key) and value: group["unit"][key] = value
            origin = {k: source_row[k] for k in ("source", "sheet_id", "worksheet", "row_number", "row_hash")}
            origin["header_found"] = source_row.get("header_found", True)
            group["rows"].append(origin)
            group["representative_error"] = group.get("representative_error") or representative_error
        else:
            index = len(groups)
            origin = {k: source_row[k] for k in ("source", "sheet_id", "worksheet", "row_number", "row_hash")}
            origin["header_found"] = source_row.get("header_found", True)
            group = {"unit": unit, "rows": [origin], "products": [],
                     "representative_error": representative_error}
            groups.append(group)
        for kind, value in keys: indexes[kind].setdefault(value, index)
        known = {normalize(p["name"]) for p in group["products"]}
        for product in products:
            key = normalize(product["name"])
            if key and key not in known and len(group["products"]) < MAX_PRODUCTS:
                group["products"].append(product); known.add(key)
    valid, errors_by_reason, valid_rows = [], Counter(), set()
    for group in groups:
        reasons = _validation_reasons(group)
        group.pop("representative_error", None)
        for row in group["rows"]:
            row.pop("header_found", None)
        if reasons:
            invalid.append({"rows": group["rows"], "reasons": reasons})
            errors_by_reason.update(reason["reason"] for reason in reasons)
        else:
            valid.append(group)
            valid_rows.update(_row_key(row) for row in group["rows"])
    errors_by_reason["posible_duplicado"] += len(conflicts)
    if not errors_by_reason["posible_duplicado"]:
        del errors_by_reason["posible_duplicado"]
    source_summary = {}
    for source, label, rows_for_source in (
        ("GENERAL", "general", general_source_rows), ("CORRECTED", "corrected", corrected_source_rows)
    ):
        read = len(rows_for_source)
        valid_count = sum(_row_key(row) in valid_rows for row in rows_for_source)
        source_summary[label] = {"rows_read": read, "valid": valid_count, "invalid": read - valid_count}
    summary = {"responses_read": len(source_rows), "unique_units": len(valid), "merged_units": merged,
               "possible_duplicates": len(conflicts), "invalid_units": len(invalid),
               "products_detected": sum(len(g["products"]) for g in valid), "new_products": sum(len(g["products"]) for g in valid),
               "ambiguous_products": len(ambiguous), "logos": sum(bool(g["unit"]["logo_drive_id"]) for g in valid),
               "photos": sum(len(p["images"]) for g in valid for p in g["products"]),
               "assigned_photos": sum(len(p["images"]) for g in valid for p in g["products"]), "ambiguous_photos": 0,
               "errors": len(conflicts) + len(invalid), "warnings": len(ambiguous),
               "errors_by_reason": dict(sorted(errors_by_reason.items())), "sources": source_summary}
    plan = {"schema_version": 1, "sources": {"general": {"sheet_id": general_id, "hash": sha(general_document)},
            "corrected": {"sheet_id": corrected_id, "hash": sha(corrected_document)}}, "units": valid,
            "conflicts": conflicts, "invalid_units": invalid, "ambiguous_products": ambiguous,
            "source_diagnostics": {"general": general_diagnostics, "corrected": corrected_diagnostics},
            "summary": summary}
    plan["plan_hash"] = sha(plan)
    return plan
