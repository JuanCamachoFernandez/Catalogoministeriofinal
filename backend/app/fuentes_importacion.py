import hashlib
import io
import json
import re
import unicodedata
from pathlib import Path

import click

SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
)
MAX_PRODUCTS = 15
MAX_IMAGES = 3

ALIASES = {
    "business_name": ("nombre comercial", "unidad productiva", "emprendimiento", "nombre del emprendimiento"),
    "legal_name": ("razon social", "razón social"),
    "nit": ("nit", "numero de nit", "número de nit"),
    "email": ("correo electronico", "correo electrónico", "email", "correo"),
    "phone": ("telefono whatsapp", "teléfono whatsapp", "celular", "telefono", "teléfono"),
    "first_names": ("nombres representante", "nombres del representante", "nombre responsable"),
    "paternal_name": ("apellido paterno representante", "apellido paterno"),
    "maternal_name": ("apellido materno representante", "apellido materno"),
    "department": ("departamento",),
    "address": ("direccion fisica", "dirección física", "direccion", "dirección"),
    "review": ("resena comercial", "reseña comercial", "descripcion del emprendimiento", "descripción del emprendimiento"),
    "sectors": ("sectores", "sector productivo", "rubros"),
    "logo": ("logo", "logo drive", "id logo"),
    "products": ("productos", "productos que elabora", "descripcion de productos", "descripción de productos"),
    "facebook": ("facebook",), "instagram": ("instagram",), "tiktok": ("tiktok",),
    "seprec": ("registro seprec", "seprec"), "pro_bolivia": ("registro pro bolivia", "pro bolivia"),
}


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c)).lower().strip()
    return re.sub(r"\s+", " ", value)


NORMALIZED_ALIASES = {key: tuple(normalize(v) for v in values) for key, values in ALIASES.items()}


def sha(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def field(row, name):
    normalized = {normalize(k): str(v or "").strip() for k, v in row.items()}
    return next((normalized[a] for a in NORMALIZED_ALIASES[name] if normalized.get(a)), "")


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


def rows(document, source, sheet_id):
    result = []
    for worksheet in document["worksheets"]:
        values = worksheet["values"]
        if not values:
            continue
        headers = [str(v).strip() for v in values[0]]
        for number, values_row in enumerate(values[1:], 2):
            row = {header: values_row[i] if i < len(values_row) else "" for i, header in enumerate(headers) if header}
            if any(str(v).strip() for v in row.values()):
                result.append({"source": source, "sheet_id": sheet_id, "worksheet": worksheet["title"],
                               "row_number": number, "row_hash": sha(row), "data": row})
    return result


def _worksheet_dicts(worksheet):
    values = worksheet.get("values") or []
    if not values:
        return []
    headers = [str(value).strip() for value in values[0]]
    return [
        {header: values_row[index] if index < len(values_row) else "" for index, header in enumerate(headers) if header}
        for values_row in values[1:]
        if any(str(value).strip() for value in values_row)
    ]


def _any_field(row, names):
    normalized = {normalize(key): str(value or "").strip() for key, value in row.items()}
    return next((normalized[normalize(name)] for name in names if normalized.get(normalize(name))), "")


def corrected_rows(document, sheet_id):
    """Flatten the prior relational template (units/sectors/products/images) when present."""
    worksheets = {normalize(item["title"]): item for item in document["worksheets"]}
    units_sheet = next((item for title, item in worksheets.items() if "unidad" in title), None)
    products_sheet = next((item for title, item in worksheets.items() if "producto" in title and "imagen" not in title), None)
    if not units_sheet or not products_sheet:
        return rows(document, "CORRECTED", sheet_id)
    unit_rows, product_rows = _worksheet_dicts(units_sheet), _worksheet_dicts(products_sheet)
    sector_sheet = next((item for title, item in worksheets.items() if "sector" in title), None)
    image_sheet = next((item for title, item in worksheets.items() if "imagen" in title or "foto" in title), None)
    sectors, images = _worksheet_dicts(sector_sheet or {}), _worksheet_dicts(image_sheet or {})
    unit_ref_names = ("id unidad", "codigo unidad", "código unidad", "unidad id", "unidad_productiva_id", "nombre comercial")
    product_ref_names = ("id producto", "codigo producto", "código producto", "producto id", "producto_id", "nombre producto", "producto")
    result = []
    for number, unit_row in enumerate(unit_rows, 2):
        unit_ref = normalize(_any_field(unit_row, unit_ref_names) or field(unit_row, "business_name"))
        related_products = [row for row in product_rows if normalize(_any_field(row, unit_ref_names)) == unit_ref]
        related_sectors = [row for row in sectors if normalize(_any_field(row, unit_ref_names)) == unit_ref]
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
            related_images = [row for row in images if normalize(_any_field(row, product_ref_names)) == product_ref]
            for image_number, image_row in enumerate(related_images[:MAX_IMAGES], 1):
                enriched[f"Producto {product_number} imagen {image_number}"] = _any_field(
                    image_row, ("drive id", "id drive", "archivo drive", "imagen", "foto", "url")
                )
        result.append({"source": "CORRECTED", "sheet_id": sheet_id, "worksheet": units_sheet["title"],
                       "row_number": number, "row_hash": sha(enriched), "data": enriched})
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
            return [], raw
        products = [{"name": name, "description": "", "images": [],
                     "origin": {k: source_row[k] for k in ("source", "sheet_id", "worksheet", "row_number", "row_hash")}}
                    for name in clear[:MAX_PRODUCTS]]
    return products, None


def unit_payload(source_row):
    row = source_row["data"]
    return {
        "business_name": field(row, "business_name"), "legal_name": field(row, "legal_name"),
        "nit": re.sub(r"\D", "", field(row, "nit")), "email": field(row, "email").lower(),
        "phone": re.sub(r"[^0-9+]", "", field(row, "phone")), "first_names": field(row, "first_names"),
        "paternal_name": field(row, "paternal_name"), "maternal_name": field(row, "maternal_name"),
        "department": field(row, "department"), "address": field(row, "address"), "review": field(row, "review"),
        "facebook": field(row, "facebook"), "instagram": field(row, "instagram"), "tiktok": field(row, "tiktok"),
        "seprec": field(row, "seprec"), "pro_bolivia": field(row, "pro_bolivia"),
        "sectors": clear_items(field(row, "sectors")), "logo_drive_id": drive_id(field(row, "logo")),
    }


def build_plan(general_document, corrected_document, general_id, corrected_id):
    source_rows = corrected_rows(corrected_document, corrected_id) + rows(general_document, "GENERAL", general_id)
    groups, indexes = [], {"nit": {}, "email": {}, "email_phone": {}, "name": {}}
    conflicts, invalid, ambiguous, merged = [], [], [], 0
    for source_row in source_rows:
        unit, (products, unclear) = unit_payload(source_row), row_products(source_row)
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
            group["rows"].append({k: source_row[k] for k in ("source", "sheet_id", "worksheet", "row_number", "row_hash")})
        else:
            index = len(groups)
            group = {"unit": unit, "rows": [{k: source_row[k] for k in ("source", "sheet_id", "worksheet", "row_number", "row_hash")}], "products": []}
            groups.append(group)
        for kind, value in keys: indexes[kind].setdefault(value, index)
        known = {normalize(p["name"]) for p in group["products"]}
        for product in products:
            key = normalize(product["name"])
            if key and key not in known and len(group["products"]) < MAX_PRODUCTS:
                group["products"].append(product); known.add(key)
    required = ("business_name", "legal_name", "email", "phone", "first_names", "paternal_name", "maternal_name", "department", "address", "review")
    valid = []
    for group in groups:
        missing = [key for key in required if not group["unit"].get(key)]
        if missing: invalid.append({"rows": group["rows"], "business_name": group["unit"].get("business_name"), "missing": missing})
        else: valid.append(group)
    summary = {"responses_read": len(source_rows), "unique_units": len(valid), "merged_units": merged,
               "possible_duplicates": len(conflicts), "invalid_units": len(invalid),
               "products_detected": sum(len(g["products"]) for g in valid), "new_products": sum(len(g["products"]) for g in valid),
               "ambiguous_products": len(ambiguous), "logos": sum(bool(g["unit"]["logo_drive_id"]) for g in valid),
               "photos": sum(len(p["images"]) for g in valid for p in g["products"]),
               "assigned_photos": sum(len(p["images"]) for g in valid for p in g["products"]), "ambiguous_photos": 0,
               "errors": len(conflicts) + len(invalid), "warnings": len(ambiguous)}
    plan = {"schema_version": 1, "sources": {"general": {"sheet_id": general_id, "hash": sha(general_document)},
            "corrected": {"sheet_id": corrected_id, "hash": sha(corrected_document)}}, "units": valid,
            "conflicts": conflicts, "invalid_units": invalid, "ambiguous_products": ambiguous, "summary": summary}
    plan["plan_hash"] = sha(plan)
    return plan
