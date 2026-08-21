import hashlib
import io
import json
import re
import unicodedata
from collections import Counter
from decimal import Decimal, InvalidOperation
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
    "product_photos": (
        "fotografias de los productos", "fotografías de los productos",
        "fotografias productos", "fotografías productos", "fotos productos",
    ),
    "facebook": ("facebook",), "instagram": ("instagram",), "tiktok": ("tiktok",),
    "seprec": ("registro seprec", "seprec"), "pro_bolivia": ("registro pro bolivia", "pro bolivia"),
}

UNIT_INFORMATIONAL_FIELDS = (
    "legal_name", "nit", "phone", "address", "review", "maternal_name",
    "facebook", "instagram", "tiktok", "seprec", "pro_bolivia", "logo_drive_id",
)
CORE_HEADER_FIELDS = ("business_name", "email", "phone", "representative_name", "first_names")
DEPARTMENTS = {
    "beni": "Beni", "chuquisaca": "Chuquisaca", "cochabamba": "Cochabamba",
    "la paz": "La Paz", "oruro": "Oruro", "pando": "Pando", "potosi": "Potosí",
    "santa cruz": "Santa Cruz", "tarija": "Tarija",
}
UNIT_REF_NAMES = (
    "id unidad", "id_unidad", "unidad id", "unidad_id", "unidad_productiva_id",
    "id up", "id_up", "up id", "up_id", "codigo unidad", "código unidad",
    "id de unidad", "id de la unidad", "id de up", "id de la up",
    "codigo_unidad", "codigo up", "código up", "codigo_up", "codigo de unidad",
    "codigo de la unidad", "codigo de up", "codigo de la up", "unidad productiva",
    "nombre unidad", "nombre comercial", "correo electronico unidad",
    "correo electrónico unidad", "correo electronico", "correo electrónico", "unidad", "up",
)
UNIT_EMAIL_REF_NAMES = (
    "correo_electronico_unidad", "correo electronico unidad", "correo electrónico unidad",
    "correo_electronico", "correo electronico", "correo electrónico",
)
PRODUCT_REF_NAMES = (
    "id producto", "id_producto", "producto id", "producto_id", "codigo producto",
    "código producto", "codigo_producto", "id del producto", "codigo del producto",
    "codigo prod", "id prod", "nombre producto",
    "producto",
)
PRODUCT_NAME_NAMES = ("nombre producto", "nombre del producto", "producto", "nombre comercial", "nombre")
IMAGE_PRODUCT_NAME_NAMES = (
    "nombre_comercial_producto", "nombre comercial producto", "nombre comercial del producto",
    "nombre producto", "producto",
)
PRODUCT_DESCRIPTION_NAMES = (
    "descripcion producto", "descripción producto", "descripcion tecnica", "descripción técnica",
    "descripcion", "descripción",
)
PRODUCT_PRICE_NAMES = ("precio referencia", "precio de referencia", "precio referencial", "precio", "costo")
PRODUCT_PRESENTATION_NAMES = (
    "presentacion empaque", "presentación empaque", "presentacion", "presentación", "empaque",
)
PRODUCT_STOCK_NAMES = (
    "capacidad produccion stock", "capacidad de produccion", "capacidad de producción",
    "capacidad stock", "stock", "capacidad",
)
IMAGE_VALUE_NAMES = (
    "drive id", "id drive", "drive file id", "archivo drive", "id archivo",
    "enlace drive", "url drive", "url_imagen", "url imagen", "imagen url", "imagen", "foto", "url",
)
PRODUCT_MATERIAL_NAMES = ("materia_prima", "materia prima", "materiales", "ingredientes")
PRODUCT_DIMENSION_NAMES = ("dimensiones", "dimension", "medidas")
PRODUCT_COLOR_NAMES = ("colores_disponibles", "colores disponibles", "colores")
PRODUCT_CERTIFICATION_NAMES = ("certificaciones", "certificacion", "certificación")
PRODUCT_CATEGORY_NAMES = ("categoria_nombre", "categoria nombre", "categoría nombre", "categoria", "categoría")
PRODUCT_DESIRED_STATUS_NAMES = ("estado_deseado", "estado deseado")


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c)).lower().strip()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()


NORMALIZED_ALIASES = {key: tuple(normalize(v) for v in values) for key, values in ALIASES.items()}
UNIT_ONLY_FIELDS = set(ALIASES) - {"products", "product_photos"}


def sha(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def plan_sha256(plan):
    """Return the canonical hash without trusting a hash embedded in the plan."""
    return sha({key: value for key, value in plan.items() if key != "plan_hash"})


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
        if name in UNIT_ONLY_FIELDS and "producto" in normalized_header:
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


def drive_ids(value):
    """Extract every Drive ID from a multi-link cell while preserving order."""
    raw = str(value or "").strip()
    if not raw:
        return []
    matches = re.findall(r"(?:/d/|[?&]id=)([A-Za-z0-9_-]{20,})", raw)
    if matches:
        return matches
    result = []
    for item in re.split(r"[,;\n]+", raw):
        identifier = drive_id(item.strip())
        if identifier:
            result.append(identifier)
    return result


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


def _extra_header_matches(headers, aliases):
    return sum(
        any(_header_score(normalize(header), normalize(alias)) for alias in aliases)
        for header in headers if str(header).strip()
    )


def _header_row(values, extra_aliases=()):
    """Find the header row instead of assuming that it is always row one."""
    candidates = []
    for index, values_row in enumerate(values[:20]):
        headers = [str(value).strip() for value in values_row]
        recognized = _recognized_fields(headers)
        score = len(recognized) + _extra_header_matches(headers, extra_aliases)
        candidates.append((score, len([header for header in headers if header]), -index, index, headers, recognized))
    if not candidates:
        return None, [], []
    _score, _width, _position, index, headers, recognized = max(candidates)
    return index, headers, recognized


def _worksheet_dicts(worksheet, extra_aliases=()):
    values = worksheet.get("values") or []
    if not values:
        return [], {"header_row": None, "recognized_fields": [], "header_found": False, "rows_read": 0}
    header_index, headers, recognized = _header_row(values, extra_aliases)
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
        "header_found": any(name in recognized for name in CORE_HEADER_FIELDS)
                        or bool(_extra_header_matches(headers, extra_aliases)),
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
    _header, value = _any_field_match(row, names)
    return value


def _any_field_match(row, names):
    for name in names:
        candidates = []
        for key, value in row.items():
            score = _header_score(normalize(key), normalize(name))
            if score and str(value or "").strip():
                candidates.append((score, str(key), str(value).strip()))
        if candidates:
            _score, header, value = max(candidates)
            return header, value
    return "", ""


def _reference_values(row, names):
    values = set()
    for name in names:
        for key, value in row.items():
            if _header_score(normalize(key), normalize(name)) and str(value or "").strip():
                values.add(normalize(value))
    return values


def _unit_reference_values(row):
    values = _reference_values(row, UNIT_REF_NAMES)
    email = _unit_email(row)
    if email:
        values.add(f"email:{email}")
    return values


def _unit_email(row):
    return _any_field(row, UNIT_EMAIL_REF_NAMES).strip().casefold()


def _product_name(row):
    filtered = {
        key: value for key, value in row.items()
        if "id" not in normalize(key).split() and "codigo" not in normalize(key).split()
    }
    return _any_field(filtered, PRODUCT_NAME_NAMES)


def _price_value(value):
    raw = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not raw:
        return None, False
    try:
        parsed = Decimal(raw)
    except InvalidOperation:
        return None, True
    if parsed < 0:
        return None, True
    return format(parsed, "f"), False


def _product_complete(product):
    return bool(
        product.get("description") and product.get("price") is not None
        and product.get("material") and product.get("presentation")
        and product.get("stock") and product.get("images")
    )


def _empty_corrected_audit():
    return {
        "products": {"rows_read": 0, "detected": 0, "valid": 0, "draft": 0,
                     "invalid": 0, "without_unit": 0},
        "images": {"rows_read": 0, "drive_ids_detected": 0, "assigned": 0,
                   "without_product": 0, "ambiguous": 0},
        "sectors": {"rows_read": 0, "associated": 0, "without_unit": 0},
        "warnings": [],
    }


def _image_product_matches(image_row, product_rows):
    image_unit_refs = _unit_reference_values(image_row)
    image_email = _unit_email(image_row)
    image_name = normalize(_any_field(image_row, IMAGE_PRODUCT_NAME_NAMES))
    if image_email and image_name:
        return [
            (number, product_row) for number, product_row in product_rows
            if _unit_email(product_row) == image_email
            and normalize(_product_name(product_row)) == image_name
        ]
    if image_unit_refs and image_name:
        return [
            (number, product_row) for number, product_row in product_rows
            if _unit_reference_values(product_row) & image_unit_refs
            and normalize(_product_name(product_row)) == image_name
        ]
    image_product_refs = _reference_values(image_row, PRODUCT_REF_NAMES)
    matches = []
    for number, product_row in product_rows:
        if not (_reference_values(product_row, PRODUCT_REF_NAMES) & image_product_refs):
            continue
        if image_unit_refs and not (_unit_reference_values(product_row) & image_unit_refs):
            continue
        matches.append((number, product_row))
    return matches


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
    product_headers = UNIT_REF_NAMES + PRODUCT_REF_NAMES + PRODUCT_NAME_NAMES + PRODUCT_DESCRIPTION_NAMES \
        + PRODUCT_PRICE_NAMES + PRODUCT_PRESENTATION_NAMES + PRODUCT_STOCK_NAMES + PRODUCT_MATERIAL_NAMES \
        + PRODUCT_DIMENSION_NAMES + PRODUCT_COLOR_NAMES + PRODUCT_CERTIFICATION_NAMES \
        + PRODUCT_CATEGORY_NAMES + PRODUCT_DESIRED_STATUS_NAMES
    product_rows, product_metadata = _worksheet_dicts(products_sheet or {}, product_headers)
    sectors, sector_metadata = _worksheet_dicts(sector_sheet or {}, UNIT_REF_NAMES + ("sector", "nombre sector"))
    images, image_metadata = _worksheet_dicts(image_sheet or {}, UNIT_REF_NAMES + PRODUCT_REF_NAMES + IMAGE_VALUE_NAMES)
    result = []
    for number, unit_row in unit_rows:
        unit_refs = _unit_reference_values(unit_row)
        if field(unit_row, "business_name"):
            unit_refs.add(normalize(field(unit_row, "business_name")))
        related_products = [(row_number, row) for row_number, row in product_rows
                            if _unit_reference_values(row) & unit_refs]
        related_sectors = [row for _row_number, row in sectors
                           if _unit_reference_values(row) & unit_refs]
        enriched = dict(unit_row)
        sector_names = [_any_field(row, ("sector", "sector productivo", "nombre sector")) for row in related_sectors]
        if sector_names:
            enriched["Sectores"] = "; ".join(name for name in sector_names if name)
        product_origins = {}
        for product_number, (product_row_number, product_row) in enumerate(related_products[:MAX_PRODUCTS], 1):
            enriched[f"Producto {product_number}"] = _product_name(product_row)
            enriched[f"Producto {product_number} descripcion"] = _any_field(product_row, PRODUCT_DESCRIPTION_NAMES)
            enriched[f"Producto {product_number} precio"] = _any_field(product_row, PRODUCT_PRICE_NAMES)
            enriched[f"Producto {product_number} presentacion"] = _any_field(product_row, PRODUCT_PRESENTATION_NAMES)
            enriched[f"Producto {product_number} stock"] = _any_field(product_row, PRODUCT_STOCK_NAMES)
            enriched[f"Producto {product_number} materia prima"] = _any_field(product_row, PRODUCT_MATERIAL_NAMES)
            enriched[f"Producto {product_number} dimensiones"] = _any_field(product_row, PRODUCT_DIMENSION_NAMES)
            enriched[f"Producto {product_number} colores"] = _any_field(product_row, PRODUCT_COLOR_NAMES)
            enriched[f"Producto {product_number} certificaciones"] = _any_field(product_row, PRODUCT_CERTIFICATION_NAMES)
            enriched[f"Producto {product_number} categoria"] = _any_field(product_row, PRODUCT_CATEGORY_NAMES)
            enriched[f"Producto {product_number} estado deseado"] = _any_field(product_row, PRODUCT_DESIRED_STATUS_NAMES)
            product_name_row = {
                key: value for key, value in product_row.items()
                if "id" not in normalize(key).split() and "codigo" not in normalize(key).split()
            }
            name_header, _name_value = _any_field_match(product_name_row, PRODUCT_NAME_NAMES)
            product_origins[product_number] = {
                "source": "CORRECTED", "sheet_id": sheet_id, "worksheet": products_sheet["title"],
                "row_number": product_row_number, "row_hash": sha(product_row),
                "field_headers": {
                    "nombre": name_header, "nombre_comercial": name_header,
                    "descripcion": _any_field_match(product_row, PRODUCT_DESCRIPTION_NAMES)[0],
                    "descripcion_tecnica": _any_field_match(product_row, PRODUCT_DESCRIPTION_NAMES)[0],
                    "presentacion": _any_field_match(product_row, PRODUCT_PRESENTATION_NAMES)[0],
                    "presentacion_empaque": _any_field_match(product_row, PRODUCT_PRESENTATION_NAMES)[0],
                    "precio_referencia": _any_field_match(product_row, PRODUCT_PRICE_NAMES)[0],
                    "precio": _any_field_match(product_row, PRODUCT_PRICE_NAMES)[0],
                    "capacidad_produccion_stock": _any_field_match(product_row, PRODUCT_STOCK_NAMES)[0],
                    "materia_prima": _any_field_match(product_row, PRODUCT_MATERIAL_NAMES)[0],
                    "dimensiones": _any_field_match(product_row, PRODUCT_DIMENSION_NAMES)[0],
                    "colores_disponibles": _any_field_match(product_row, PRODUCT_COLOR_NAMES)[0],
                    "certificaciones": _any_field_match(product_row, PRODUCT_CERTIFICATION_NAMES)[0],
                },
            }
            related_images = [row for _row_number, row in images
                              if len(_image_product_matches(row, product_rows)) == 1
                              and _image_product_matches(row, product_rows)[0][0] == product_row_number]
            for image_number, image_row in enumerate(related_images[:MAX_IMAGES], 1):
                enriched[f"Producto {product_number} imagen {image_number}"] = _any_field(
                    image_row, IMAGE_VALUE_NAMES
                )
        result.append({"source": "CORRECTED", "sheet_id": sheet_id, "worksheet": units_sheet["title"],
                       "row_number": number, "row_hash": sha(enriched), "data": enriched,
                       "header_found": unit_metadata["header_found"],
                       "product_origins": product_origins})
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


def _corrected_audit(document):
    audit = _empty_corrected_audit()
    worksheets = {normalize(item["title"]): item for item in document.get("worksheets", [])}
    units_sheet = next((item for title, item in worksheets.items() if "unidad" in title), None)
    products_sheet = next((item for title, item in worksheets.items() if "producto" in title and "imagen" not in title), None)
    images_sheet = next((item for title, item in worksheets.items() if "imagen" in title or "foto" in title), None)
    sectors_sheet = next((item for title, item in worksheets.items() if "sector" in title), None)
    if not units_sheet or not products_sheet:
        return audit
    unit_rows, _unit_metadata = _worksheet_dicts(units_sheet)
    product_headers = UNIT_REF_NAMES + PRODUCT_REF_NAMES + PRODUCT_NAME_NAMES + PRODUCT_DESCRIPTION_NAMES \
        + PRODUCT_PRICE_NAMES + PRODUCT_PRESENTATION_NAMES + PRODUCT_STOCK_NAMES + PRODUCT_MATERIAL_NAMES \
        + PRODUCT_DIMENSION_NAMES + PRODUCT_COLOR_NAMES + PRODUCT_CERTIFICATION_NAMES \
        + PRODUCT_CATEGORY_NAMES + PRODUCT_DESIRED_STATUS_NAMES
    product_rows, _product_metadata = _worksheet_dicts(products_sheet, product_headers)
    image_rows, _image_metadata = _worksheet_dicts(
        images_sheet or {}, UNIT_REF_NAMES + PRODUCT_REF_NAMES + IMAGE_VALUE_NAMES
    )
    sector_rows, _sector_metadata = _worksheet_dicts(
        sectors_sheet or {}, UNIT_REF_NAMES + ("sector_nombre", "sector nombre", "sector")
    )
    unit_references = []
    for _number, unit_row in unit_rows:
        references = _unit_reference_values(unit_row)
        if field(unit_row, "business_name"):
            references.add(normalize(field(unit_row, "business_name")))
        unit_references.append(references)
    audit["products"]["rows_read"] = len(product_rows)
    audit["images"]["rows_read"] = len(image_rows)
    audit["sectors"]["rows_read"] = len(sector_rows)
    for number, sector_row in sector_rows:
        matches = [unit for unit in unit_references if unit & _unit_reference_values(sector_row)]
        if len(matches) == 1:
            audit["sectors"]["associated"] += 1
        else:
            audit["sectors"]["without_unit"] += 1
            audit["warnings"].append({"reason": "sector_sin_unidad_relacionada", "severity": "informative",
                                      "pending": True, "source": "CORRECTED",
                                      "worksheet": sectors_sheet["title"], "row": number})
    assigned_image_rows = set()
    assigned_images = {}
    for image_number, image_row in image_rows:
        image_id = drive_id(_any_field(image_row, IMAGE_VALUE_NAMES))
        matches = [(product_number, row) for product_number, row in _image_product_matches(image_row, product_rows)
                   if _product_name(row)]
        if image_id and len(matches) == 1:
            product_number = matches[0][0]
            product_images = assigned_images.setdefault(product_number, [])
            if len(product_images) < MAX_IMAGES:
                product_images.append(image_id)
                assigned_image_rows.add(image_number)
    for number, product_row in product_rows:
        name = _product_name(product_row)
        if not name:
            audit["products"]["invalid"] += 1
            audit["warnings"].append({"reason": "producto_sin_nombre", "severity": "informative",
                                      "pending": True, "source": "CORRECTED",
                                      "worksheet": products_sheet["title"], "row": number})
            continue
        audit["products"]["detected"] += 1
        references = _unit_reference_values(product_row)
        matches = [unit for unit in unit_references if unit & references]
        if len(matches) != 1:
            audit["products"]["without_unit"] += 1
            reason = "producto_unidad_ambigua" if len(matches) > 1 else "producto_sin_unidad_relacionada"
            audit["warnings"].append({"reason": reason, "severity": "informative",
                                      "pending": True, "source": "CORRECTED",
                                      "worksheet": products_sheet["title"], "row": number})
            continue
        price, invalid_price = _price_value(_any_field(product_row, PRODUCT_PRICE_NAMES))
        if invalid_price:
            audit["warnings"].append({"reason": "precio_producto_invalido", "severity": "informative",
                                      "source": "CORRECTED", "worksheet": products_sheet["title"], "row": number})
        images = assigned_images.get(number, [])
        product = {
            "description": _any_field(product_row, PRODUCT_DESCRIPTION_NAMES), "price": price,
            "material": _any_field(product_row, PRODUCT_MATERIAL_NAMES),
            "presentation": _any_field(product_row, PRODUCT_PRESENTATION_NAMES),
            "stock": _any_field(product_row, PRODUCT_STOCK_NAMES), "images": images,
        }
        status = "valid" if _product_complete(product) else "draft"
        audit["products"][status] += 1
        if status == "draft":
            audit["warnings"].append({"reason": "producto_incompleto_draft", "severity": "informative",
                                      "source": "CORRECTED", "worksheet": products_sheet["title"], "row": number})
    for number, image_row in image_rows:
        raw_image = _any_field(image_row, IMAGE_VALUE_NAMES)
        image_id = drive_id(raw_image)
        if not image_id:
            if raw_image:
                audit["images"]["ambiguous"] += 1
                audit["warnings"].append({"reason": "imagen_drive_invalida", "severity": "informative",
                                          "pending": True, "source": "CORRECTED",
                                          "worksheet": images_sheet["title"], "row": number})
            continue
        audit["images"]["drive_ids_detected"] += 1
        matches = [(product_number, row) for product_number, row in _image_product_matches(image_row, product_rows)
                   if _product_name(row)]
        if not matches:
            audit["images"]["without_product"] += 1
            audit["warnings"].append({"reason": "imagen_sin_producto", "severity": "informative",
                                      "pending": True, "source": "CORRECTED",
                                      "worksheet": images_sheet["title"], "row": number})
        elif len(matches) > 1:
            audit["images"]["ambiguous"] += 1
            audit["warnings"].append({"reason": "imagen_producto_ambiguo", "severity": "informative",
                                      "pending": True, "source": "CORRECTED",
                                      "worksheet": images_sheet["title"], "row": number})
        elif number in assigned_image_rows:
            audit["images"]["assigned"] += 1
        else:
            audit["images"]["ambiguous"] += 1
            audit["warnings"].append({"reason": "limite_imagenes_producto", "severity": "informative",
                                      "pending": True, "source": "CORRECTED",
                                      "worksheet": images_sheet["title"], "row": number})
    return audit


def row_products(source_row):
    row = source_row["data"]
    normalized = {normalize(k): str(v or "").strip() for k, v in row.items()}
    normalized_headers = {normalize(k): str(k) for k in row}
    products = []
    for number in range(1, MAX_PRODUCTS + 1):
        name = next((normalized.get(k) for k in (f"producto {number}", f"producto {number} nombre", f"nombre producto {number}") if normalized.get(k)), "")
        if not name:
            continue
        name_key = next((key for key in (
            f"producto {number}", f"producto {number} nombre", f"nombre producto {number}"
        ) if normalized.get(key)), "")
        description = next((normalized.get(k) for k in (f"producto {number} descripcion", f"descripcion producto {number}") if normalized.get(k)), "")
        price_raw = next((normalized.get(k) for k in (f"producto {number} precio", f"precio producto {number}") if normalized.get(k)), "")
        price, invalid_price = _price_value(price_raw)
        presentation = next((normalized.get(k) for k in (f"producto {number} presentacion", f"presentacion producto {number}") if normalized.get(k)), "")
        stock = next((normalized.get(k) for k in (f"producto {number} stock", f"stock producto {number}",
                                                   f"producto {number} capacidad") if normalized.get(k)), "")
        material = normalized.get(f"producto {number} materia prima", "")
        dimensions = normalized.get(f"producto {number} dimensiones", "")
        colors = normalized.get(f"producto {number} colores", "")
        certifications = normalized.get(f"producto {number} certificaciones", "")
        category = normalized.get(f"producto {number} categoria", "")
        desired_status = normalized.get(f"producto {number} estado deseado", "")
        images = []
        image_values_seen = invalid_images = 0
        for image_number in range(1, MAX_IMAGES + 1):
            value = next((normalized.get(k) for k in (f"producto {number} imagen {image_number}", f"imagen producto {number} {image_number}", f"foto producto {number} {image_number}") if normalized.get(k)), "")
            if value:
                image_values_seen += 1
                if drive_id(value):
                    images.append(drive_id(value))
                else:
                    invalid_images += 1
        default_origin = {k: source_row[k] for k in ("source", "sheet_id", "worksheet", "row_number", "row_hash")}
        default_origin["field_headers"] = {
            "nombre": normalized_headers.get(name_key, ""),
            "nombre_comercial": normalized_headers.get(name_key, ""),
            "slug": normalized_headers.get(name_key, ""),
        }
        origin = source_row.get("product_origins", {}).get(number, default_origin)
        products.append({"name": name, "description": description, "price": price,
                         "presentation": presentation, "stock": stock, "material": material,
                         "dimensions": dimensions, "colors": colors, "certifications": certifications,
                         "category": category, "desired_status": desired_status, "images": images,
                         "invalid_price": invalid_price, "image_values_seen": image_values_seen,
                         "invalid_images": invalid_images,
                         "origin": origin})
    raw = field(row, "products")
    unclear = None
    if not products and raw:
        clear = clear_items(raw)
        if not clear:
            if "," in raw:
                unclear = raw
                clear = []
            else:
                clear = [raw]
        raw_header = _field_header(row, "products")
        raw_origin = {k: source_row[k] for k in ("source", "sheet_id", "worksheet", "row_number", "row_hash")}
        raw_origin["field_headers"] = {"nombre": raw_header, "nombre_comercial": raw_header, "slug": raw_header}
        products = [{"name": name, "description": "", "price": None, "presentation": "", "stock": "",
                     "material": "", "dimensions": "", "colors": "", "certifications": "",
                     "category": "", "desired_status": "", "images": [], "invalid_price": False,
                     "image_values_seen": 0, "invalid_images": 0,
                     "origin": raw_origin}
                    for name in clear[:MAX_PRODUCTS]]
    general_photo_ids = drive_ids(field(row, "product_photos"))
    photo_audit = {"detected": len(general_photo_ids), "assigned": 0, "ambiguous": 0}
    if general_photo_ids:
        if len(products) == 1:
            proposed = general_photo_ids[:MAX_IMAGES]
            products[0]["images"].extend(proposed)
            photo_audit["assigned"] = len(proposed)
            photo_audit["ambiguous"] = len(general_photo_ids) - len(proposed)
        elif products and len(general_photo_ids) == MAX_IMAGES * len(products):
            for index, product in enumerate(products):
                product["images"].extend(general_photo_ids[index * MAX_IMAGES:(index + 1) * MAX_IMAGES])
            photo_audit["assigned"] = len(general_photo_ids)
        else:
            photo_audit["ambiguous"] = len(general_photo_ids)
    return products, unclear, photo_audit


def _split_representative(row, first_names, paternal_name, maternal_name):
    if first_names and paternal_name:
        return first_names, paternal_name, maternal_name or "", None
    full_name = field(row, "representative_name")
    if not full_name:
        return first_names, paternal_name, maternal_name, None
    parts = [part for part in re.split(r"\s+", full_name.strip()) if part]
    if len(parts) < 2:
        return first_names, paternal_name, maternal_name, "representante_no_divisible"
    if len(parts) == 2:
        return parts[0], parts[1], "", None
    return " ".join(parts[:-2]), parts[-2], parts[-1], None


def _canonical_phone(value):
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 11 and digits.startswith("591"):
        digits = digits[3:]
    elif len(digits) == 9 and digits.startswith("0"):
        digits = digits[1:]
    return digits


def _optional_text(value, max_length, *, pattern=None):
    value = str(value or "").strip()
    if not value:
        return "", False
    invalid = len(value) > max_length or (pattern is not None and not re.fullmatch(pattern, value, re.I))
    return ("" if invalid else value), invalid


def unit_payload(source_row):
    row = source_row["data"]
    logo_value = field(row, "logo")
    first_names, paternal_name, maternal_name, representative_error = _split_representative(
        row, field(row, "first_names"), field(row, "paternal_name"), field(row, "maternal_name")
    )
    department_raw = field(row, "department")
    facebook, invalid_facebook = _optional_text(field(row, "facebook"), 500)
    instagram, invalid_instagram = _optional_text(field(row, "instagram"), 500)
    tiktok, invalid_tiktok = _optional_text(
        field(row, "tiktok"), 500,
        pattern=r"https://(?:www\.)?tiktok\.com/@[^/?#\s]+[^\s]*",
    )
    seprec, invalid_seprec = _optional_text(field(row, "seprec"), 100)
    pro_bolivia, invalid_pro_bolivia = _optional_text(field(row, "pro_bolivia"), 100)
    payload = {
        "business_name": field(row, "business_name"), "legal_name": field(row, "legal_name"),
        "nit": re.sub(r"\D", "", field(row, "nit")), "email": field(row, "email").lower(),
        "phone": _canonical_phone(field(row, "phone")), "first_names": first_names,
        "paternal_name": paternal_name, "maternal_name": maternal_name,
        "department": DEPARTMENTS.get(normalize(department_raw), department_raw),
        "address": field(row, "address"), "review": field(row, "review"),
        "facebook": facebook, "instagram": instagram, "tiktok": tiktok,
        "seprec": seprec, "pro_bolivia": pro_bolivia,
        "sectors": sector_items(field(row, "sectors")), "logo_drive_id": drive_id(logo_value),
        "logo_supplied": bool(logo_value),
        "_optional_invalid": [name for name, invalid in (
            ("facebook_url", invalid_facebook), ("instagram_url", invalid_instagram),
            ("tiktok_url", invalid_tiktok), ("registro_seprec", invalid_seprec),
            ("registro_pro_bolivia", invalid_pro_bolivia),
        ) if invalid],
        "_field_headers": {
            "nombre_comercial": _field_header(row, "business_name"),
            "razon_social": _field_header(row, "legal_name"),
            "nit": _field_header(row, "nit"), "correo_electronico": _field_header(row, "email"),
            "telefono_whatsapp": _field_header(row, "phone"),
            "nombres_representante": _field_header(row, "first_names") or _field_header(row, "representative_name"),
            "apellido_paterno_representante": _field_header(row, "paternal_name") or _field_header(row, "representative_name"),
            "apellido_materno_representante": _field_header(row, "maternal_name") or _field_header(row, "representative_name"),
            "departamento": _field_header(row, "department"), "direccion_fisica": _field_header(row, "address"),
            "resena_comercial": _field_header(row, "review"), "facebook_url": _field_header(row, "facebook"),
            "instagram_url": _field_header(row, "instagram"), "tiktok_url": _field_header(row, "tiktok"),
            "registro_seprec": _field_header(row, "seprec"),
            "registro_pro_bolivia": _field_header(row, "pro_bolivia"),
        },
    }
    return payload, representative_error


def _pending_unit_reasons(group):
    unit = group["unit"]
    if any(not row.get("header_found", True) for row in group["rows"]):
        return [{"reason": "encabezado_no_encontrado"}]
    reasons = []
    if not unit.get("business_name"):
        reasons.append({"reason": "unidad_no_identificable"})
    if not unit.get("email"):
        reasons.append({"reason": "correo_responsable_faltante"})
    elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", unit["email"]):
        reasons.append({"reason": "correo_responsable_invalido"})
    if not unit.get("first_names") or not unit.get("paternal_name"):
        reasons.append({"reason": "representante_no_divisible"})
    if not unit.get("department"):
        reasons.append({"reason": "departamento_faltante"})
    elif normalize(unit["department"]) not in DEPARTMENTS:
        reasons.append({"reason": "departamento_invalido"})
    return reasons


def _unit_incomplete_reasons(unit):
    reasons = [f"{field_name}_faltante" for field_name in UNIT_INFORMATIONAL_FIELDS if not unit.get(field_name)]
    if unit.get("phone") and not re.fullmatch(r"[67][0-9]{7}", unit["phone"]):
        reasons.append("telefono_invalido")
    if unit.get("nit") and not 5 <= len(unit["nit"]) <= 12:
        reasons.append("nit_invalido")
    return reasons


def _row_key(row):
    return row["source"], row["worksheet"], row["row_number"]


def _trace_rows(document, source, sheet_id, diagnostics):
    """Preserve every non-empty source row exactly as read for later review."""
    worksheets = {item.get("title", ""): item for item in document.get("worksheets", [])}
    result = []
    for diagnostic in diagnostics:
        worksheet_name = diagnostic.get("worksheet", "")
        worksheet = worksheets.get(worksheet_name, {})
        values = worksheet.get("values") or []
        header_row = diagnostic.get("header_row")
        if not header_row or header_row > len(values):
            continue
        headers = [str(value).strip() for value in values[header_row - 1]]
        for row_number, values_row in enumerate(values[header_row:], header_row + 1):
            row = {
                header: values_row[index] if index < len(values_row) else ""
                for index, header in enumerate(headers) if header
            }
            if not any(str(value).strip() for value in row.values()):
                continue
            result.append({
                "source": source, "sheet_id": sheet_id, "worksheet": worksheet_name,
                "row_number": row_number, "row_hash": sha(row), "data": row,
            })
    return result


def build_plan(general_document, corrected_document, general_id, corrected_id):
    corrected_source_rows, corrected_diagnostics = _corrected_rows(corrected_document, corrected_id)
    corrected_audit = _corrected_audit(corrected_document)
    general_source_rows, general_diagnostics = _source_rows(general_document, "GENERAL", general_id)
    source_rows = corrected_source_rows + general_source_rows
    groups, indexes = [], {"nit": {}, "email": {}, "email_phone": {}, "name": {}}
    conflicts, invalid, ambiguous, merged = [], [], [], 0
    warnings = list(corrected_audit["warnings"])
    general_products = {"detected": 0, "valid": 0, "draft": 0, "ambiguous": 0, "discarded": 0}
    image_summary = {
        "general": {"logos_detected": 0, "photos_detected": 0, "assignable": 0, "ambiguous": 0},
        "corrected": corrected_audit["images"],
    }
    image_summary["corrected"]["logos_detected"] = 0
    for source_row in source_rows:
        (unit, representative_error), (products, unclear, photo_audit) = unit_payload(source_row), row_products(source_row)
        for optional_field in unit.get("_optional_invalid", []):
            warnings.append({
                "reason": f"{optional_field}_invalido_omitido", "severity": "informative",
                "source": source_row["source"], "worksheet": source_row["worksheet"],
                "row": source_row["row_number"],
            })
        if unclear:
            issue = {"source": source_row["source"], "row": source_row["row_number"],
                     "worksheet": source_row["worksheet"], "reason": "producto_general_ambiguo"}
            ambiguous.append(issue)
            warnings.append({"reason": "producto_general_ambiguo", "severity": "informative",
                             "pending": True,
                             "source": source_row["source"], "worksheet": source_row["worksheet"],
                             "row": source_row["row_number"]})
            if source_row["source"] == "GENERAL":
                general_products["ambiguous"] += 1
        if source_row["source"] == "GENERAL":
            if unit.get("logo_drive_id"):
                image_summary["general"]["logos_detected"] += 1
            elif unit.get("logo_supplied"):
                image_summary["general"]["ambiguous"] += 1
                warnings.append({"reason": "logo_drive_invalido", "severity": "informative",
                                 "pending": True, "source": "GENERAL",
                                 "worksheet": source_row["worksheet"], "row": source_row["row_number"]})
            general_products["detected"] += len(products)
            image_summary["general"]["photos_detected"] += photo_audit["detected"]
            image_summary["general"]["ambiguous"] += photo_audit["ambiguous"]
            if photo_audit["ambiguous"]:
                warnings.append({"reason": "fotografias_generales_ambiguas", "severity": "informative",
                                 "pending": True,
                                 "source": "GENERAL", "worksheet": source_row["worksheet"],
                                 "row": source_row["row_number"]})
            for product in products:
                status = "valid" if _product_complete(product) else "draft"
                general_products[status] += 1
                image_summary["general"]["photos_detected"] += max(
                    0, product.get("image_values_seen", 0) - product.get("invalid_images", 0)
                )
                image_summary["general"]["ambiguous"] += product.get("invalid_images", 0)
                if product.get("invalid_price"):
                    warnings.append({"reason": "precio_producto_invalido", "severity": "informative",
                                     "source": "GENERAL", "worksheet": source_row["worksheet"],
                                     "row": source_row["row_number"]})
                if product.get("invalid_images"):
                    warnings.append({"reason": "imagen_drive_invalida", "severity": "informative",
                                     "pending": True, "source": "GENERAL",
                                     "worksheet": source_row["worksheet"], "row": source_row["row_number"]})
                if status == "draft":
                    warnings.append({"reason": "producto_incompleto_draft", "severity": "informative",
                                     "source": "GENERAL", "worksheet": source_row["worksheet"],
                                     "row": source_row["row_number"]})
        elif unit.get("logo_drive_id"):
            image_summary["corrected"]["logos_detected"] += 1
        elif unit.get("logo_supplied"):
            warnings.append({"reason": "logo_drive_invalido", "severity": "informative",
                             "pending": True, "source": "CORRECTED",
                             "worksheet": source_row["worksheet"], "row": source_row["row_number"]})
        keys = []
        if len(unit["nit"]) >= 5: keys.append(("nit", unit["nit"]))
        if unit["email"]:
            keys.append(("email", unit["email"]))
            if unit["phone"]: keys.append(("email_phone", f'{unit["email"]}|{unit["phone"]}'))
        if unit["business_name"]: keys.append(("name", normalize(unit["business_name"])))
        matches = {indexes[k][v] for k, v in keys if v in indexes[k]}
        if len(matches) > 1:
            conflicts.append({"source": source_row["source"], "row": source_row["row_number"],
                              "worksheet": source_row["worksheet"], "matches": sorted(matches)})
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
                conflicts.append({"source": source_row["source"], "row": source_row["row_number"],
                                  "worksheet": source_row["worksheet"],
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
    valid, pending_by_reason, valid_rows = [], Counter(), set()
    complete_units = incomplete_units = pending_products_from_units = 0
    error_rows = {"general": {}, "corrected": {}}
    for group in groups:
        reasons = _pending_unit_reasons(group)
        group.pop("representative_error", None)
        for row in group["rows"]:
            row.pop("header_found", None)
        if reasons:
            pending_products_from_units += len(group["products"])
            invalid.append({"rows": group["rows"], "reasons": reasons})
            pending_by_reason.update(reason["reason"] for reason in reasons)
            for reason in reasons:
                for row in group["rows"]:
                    source_key = "general" if row["source"] == "GENERAL" else "corrected"
                    error_rows[source_key].setdefault(reason["reason"], []).append(row["row_number"])
        else:
            incomplete_reasons = _unit_incomplete_reasons(group["unit"])
            group["completeness"] = "INCOMPLETE" if incomplete_reasons else "COMPLETE"
            group["incomplete_reasons"] = incomplete_reasons
            if incomplete_reasons:
                incomplete_units += 1
            else:
                complete_units += 1
            valid.append(group)
            valid_rows.update(_row_key(row) for row in group["rows"])
    if conflicts:
        pending_by_reason["unidad_no_identificable"] += len(conflicts)
    for conflict in conflicts:
        source_key = "general" if conflict.get("source") == "GENERAL" else "corrected"
        error_rows[source_key].setdefault("posible_duplicado", []).append(conflict["row"])
    for source_key in error_rows:
        error_rows[source_key] = {
            reason: sorted(set(numbers)) for reason, numbers in sorted(error_rows[source_key].items())
        }
    source_summary = {}
    for label, rows_for_source in (
        ("general", general_source_rows), ("corrected", corrected_source_rows)
    ):
        read = len(rows_for_source)
        valid_count = sum(_row_key(row) in valid_rows for row in rows_for_source)
        source_summary[label] = {"rows_read": read, "valid": valid_count, "invalid": 0}
    importable_products = [product for group in valid for product in group["products"]]
    general_importable = [product for product in importable_products if product["origin"]["source"] == "GENERAL"]
    general_products["discarded"] = max(0, general_products["detected"] - len(general_importable))
    image_summary["general"]["assignable"] = sum(len(product.get("images", [])) for product in general_importable)
    warning_reasons = Counter(warning["reason"] for warning in warnings)
    warning_severity = Counter(warning["severity"] for warning in warnings)
    total_products = {
        "detected": general_products["detected"] + corrected_audit["products"]["detected"],
        "importable": len(importable_products),
        "draft": sum(not _product_complete(product) for product in importable_products),
        "ambiguous": general_products["ambiguous"],
        "pending": general_products["ambiguous"] + corrected_audit["products"]["invalid"]
                   + corrected_audit["products"]["without_unit"] + pending_products_from_units,
    }
    total_images = {
        "logos": image_summary["general"]["logos_detected"] + image_summary["corrected"]["logos_detected"],
        "photos": image_summary["general"]["photos_detected"] + image_summary["corrected"]["drive_ids_detected"],
        "assigned": image_summary["general"]["assignable"] + image_summary["corrected"]["assigned"],
        "ambiguous": image_summary["general"]["ambiguous"] + image_summary["corrected"]["ambiguous"]
                     + image_summary["corrected"]["without_product"],
    }
    pending_by_reason.update(
        warning["reason"] for warning in warnings if warning.get("pending")
    )
    summary = {"responses_read": len(source_rows), "unique_units": len(valid), "merged_units": merged,
               "possible_duplicates": len(conflicts), "invalid_units": 0,
               "pending_units": len(invalid) + len(conflicts),
               "products_detected": total_products["detected"], "new_products": total_products["importable"],
               "ambiguous_products": len(ambiguous), "logos": total_images["logos"],
               "photos": total_images["photos"], "assigned_photos": total_images["assigned"],
               "ambiguous_photos": total_images["ambiguous"],
               "errors": 0, "warnings": len(warnings),
               "errors_by_reason": {}, "error_rows": {"general": {}, "corrected": {}},
               "pending_rows": error_rows,
               "pending_by_reason": dict(sorted(pending_by_reason.items())),
               "unit_classification": {"importable_complete": complete_units,
                                       "importable_incomplete": incomplete_units,
                                       "structural_pending": len(invalid) + len(conflicts)},
               "warnings_by_reason": dict(sorted(warning_reasons.items())),
               "warning_severity": {"blocking": warning_severity["blocking"],
                                    "informative": warning_severity["informative"]},
               "sources": source_summary,
               "product_sources": {"general": general_products, "corrected": corrected_audit["products"],
                                   "total": total_products},
               "sector_sources": {"corrected": corrected_audit["sectors"]},
               "image_sources": {"general": image_summary["general"], "corrected": image_summary["corrected"],
                                 "total": total_images}}
    trace_rows = (
        _trace_rows(general_document, "GENERAL", general_id, general_diagnostics)
        + _trace_rows(corrected_document, "CORRECTED", corrected_id, corrected_diagnostics)
    )
    warnings_by_row, pending_by_row = {}, {}
    for warning in warnings:
        key = (warning.get("source"), warning.get("worksheet"), warning.get("row"))
        if key[1] is not None:
            warnings_by_row.setdefault(key, []).append(warning["reason"])
            if warning.get("pending"):
                pending_by_row.setdefault(key, []).append(warning["reason"])
    for pending_group in invalid:
        for source_row in pending_group["rows"]:
            pending_by_row.setdefault(_row_key(source_row), []).extend(
                reason["reason"] for reason in pending_group["reasons"]
            )
    for conflict in conflicts:
        key = (conflict["source"], conflict["worksheet"], conflict["row"])
        pending_by_row.setdefault(key, []).append("unidad_no_identificable")
    for row in trace_rows:
        reasons = sorted(set(warnings_by_row.get(_row_key(row), [])))
        row["warnings"] = reasons
        row["ambiguous"] = bool({"producto_general_ambiguo", "fotografias_generales_ambiguas"} & set(reasons))
        row["pending_reasons"] = sorted(set(pending_by_row.get(_row_key(row), [])))
        row["pending"] = bool(row["pending_reasons"])
    plan = {"schema_version": 3, "sources": {"general": {"sheet_id": general_id, "hash": sha(general_document)},
            "corrected": {"sheet_id": corrected_id, "hash": sha(corrected_document)}}, "units": valid,
            "conflicts": conflicts, "invalid_units": invalid, "pending_units": invalid,
            "ambiguous_products": ambiguous,
            "warnings": warnings, "trace_rows": trace_rows,
            "source_diagnostics": {"general": general_diagnostics, "corrected": corrected_diagnostics},
            "summary": summary}
    plan["plan_hash"] = plan_sha256(plan)
    return plan
