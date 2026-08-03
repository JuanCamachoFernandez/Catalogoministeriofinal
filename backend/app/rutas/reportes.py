from datetime import date, datetime
from io import BytesIO
import uuid
from zoneinfo import ZoneInfo

from flask import Blueprint, request, send_file
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, or_, select

from ..extensiones import db
from ..modelos import (
    AdminProfile,
    Audit,
    Category,
    DocumentType,
    Exhibitor,
    ExhibitorType,
    ExhibitorTypeLink,
    Fair,
    FeriaStatus,
    Product,
    ProductStatus,
    Role,
    User,
    UserStatus,
)
from ..esquemas import error
from ..servicios import audit

from ..autenticacion.decoradores import roles
from ..autenticacion.permisos import ROLES_ADMINISTRACION_INSTITUCIONAL
report_bp = Blueprint("reports", __name__)
BOLIVIA_TZ = ZoneInfo("America/La_Paz")
MAX_REPORT_ROWS = 10_000

STATUS_LABELS = {
    "ACTIVE": "Activo",
    "INACTIVE": "Inactivo",
    "LOCKED": "Bloqueado",
    "AVAILABLE": "Disponible",
    "OUT_OF_STOCK": "Agotado",
    "DELETED": "Eliminado",
    "DRAFT": "En preparación",
    "PUBLISHED": "Publicada",
    "FINISHED": "Finalizada",
    "DISABLED": "Cancelada",
}
ROLE_LABELS = {
    "ADMIN": "Administrador",
    "PRODUCTIVE_UNIT_RESPONSIBLE": "Responsable de unidad productiva",
}


REPORT_COLUMNS = {
    "administradores": {
        "nombre": "Nombre completo",
        "usuario": "Usuario",
        "correo": "Correo",
        "celular": "Celular",
        "rol": "Rol",
        "cargo": "Cargo",
        "unidad": "Unidad",
        "estado": "Estado",
        "creado": "Fecha de registro",
    },
    "expositores": {
        "nombre_comercial": "Nombre comercial",
        "tipo_expositor": "Tipo de expositor",
        "nombre_tipo_expositor": "Nombre de asociación/cooperativa/emprendimiento",
        "responsable": "Responsable",
        "tipo_documento": "Tipo de documento",
        "numero_documento": "Número de documento",
        "correo": "Correo",
        "whatsapp": "WhatsApp",
        "departamento": "Departamento",
        "municipio": "Municipio",
        "direccion": "Dirección",
        "estado": "Estado",
        "creado": "Fecha de registro",
    },
    "ferias": {
        "nombre": "Feria",
        "lugar": "Lugar",
        "departamento": "Departamento",
        "direccion": "Dirección",
        "fecha_inicio": "Fecha de inicio",
        "fecha_fin": "Fecha final",
        "estado": "Estado",
        "visible": "Visible públicamente",
        "descripcion": "Descripción",
        "creado": "Fecha de registro",
    },
    "productos": {
        "nombre": "Producto",
        "expositor": "Expositor",
        "categoria": "Categoría",
        "descripcion": "Descripción",
        "estado": "Estado",
        "origen": "Lugar de origen",
        "presentacion": "Presentación",
        "creado": "Fecha de registro",
    },
    "categorias": {
        "nombre": "Categoría",
        "descripcion": "Descripción",
        "estado": "Estado",
        "creado": "Fecha de registro",
        "actualizado": "Última actualización",
    },
    "auditoria": {
        "fecha": "Fecha",
        "usuario": "Usuario",
        "accion": "Acción",
        "entidad": "Entidad",
        "descripcion": "Descripción",
        "ip": "Dirección IP",
    },
}

REPORT_TITLES = {
    "administradores": "Administradores",
    "expositores": "Expositores",
    "ferias": "Ferias",
    "productos": "Productos",
    "categorias": "Categorías",
    "auditoria": "Auditoría",
    "general": "Reporte general",
}


def enum_value(value):
    return value.value if hasattr(value, "value") else value


def display(value):
    if isinstance(value, Role):
        value = value.value
    else:
        value = enum_value(value)
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, datetime):
        local = value.astimezone(BOLIVIA_TZ) if value.tzinfo else value
        return local.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if value in STATUS_LABELS:
        return STATUS_LABELS[value]
    if value in ROLE_LABELS:
        return ROLE_LABELS[value]
    return str(value)


def parse_date(name):
    raw = request.args.get(name, "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise ValueError(f"El filtro {name} no tiene una fecha válida")


def parse_uuid(name):
    raw = request.args.get(name, "").strip()
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise ValueError(f"El filtro {name} no es válido")


def apply_created_dates(query, column):
    start = parse_date("date_from")
    end = parse_date("date_to")
    if start:
        query = query.where(func.date(column) >= start)
    if end:
        query = query.where(func.date(column) <= end)
    return query


def selected_columns(resource):
    available = REPORT_COLUMNS[resource]
    requested = [item.strip() for item in request.args.get("columns", "").split(",") if item.strip()]
    if not requested:
        return list(available)
    chosen = [item for item in requested if item in available]
    if not chosen:
        raise ValueError("Seleccione al menos una columna válida")
    return chosen


def administrator_rows():
    query = select(User, AdminProfile).outerjoin(AdminProfile).where(
        User.role == Role.ADMIN,
        User.deleted_at.is_(None),
    )
    term = request.args.get("q", "").strip()
    if term:
        pattern = f"%{term}%"
        query = query.where(or_(
            User.first_name.ilike(pattern), User.last_name.ilike(pattern),
            User.apellido_paterno.ilike(pattern), User.apellido_materno.ilike(pattern),
            User.username.ilike(pattern), User.email.ilike(pattern),
            AdminProfile.unidad.ilike(pattern),
        ))
    if request.args.get("status") in {item.value for item in UserStatus}:
        query = query.where(User.status == UserStatus(request.args["status"]))
    if request.args.get("role") == Role.ADMIN.value:
        query = query.where(User.role == Role.ADMIN)
    if request.args.get("unit"):
        query = query.where(AdminProfile.unidad == request.args["unit"])
    query = apply_created_dates(query, User.created_at).order_by(User.created_at.desc())
    rows = []
    for user, profile in db.session.execute(query.limit(MAX_REPORT_ROWS)):
        rows.append({
            "nombre": " ".join(filter(None, [user.first_name, user.apellido_paterno or user.last_name, user.apellido_materno])),
            "usuario": user.username,
            "correo": user.email,
            "celular": user.phone,
            "rol": user.role,
            "cargo": profile.cargo if profile else None,
            "unidad": profile.unidad if profile else None,
            "estado": user.status,
            "creado": user.created_at,
        })
    return rows


def exhibitor_rows():
    query = select(Exhibitor).where(Exhibitor.deleted_at.is_(None))
    term = request.args.get("q", "").strip()
    if term:
        pattern = f"%{term}%"
        query = query.where(or_(
            Exhibitor.nombre_comercial.ilike(pattern),
            Exhibitor.nombre_responsable.ilike(pattern),
            Exhibitor.apellido_responsable.ilike(pattern),
            Exhibitor.numero_documento.ilike(pattern), Exhibitor.correo.ilike(pattern),
        ))
    if request.args.get("status") in {item.value for item in UserStatus}:
        query = query.where(Exhibitor.estado == UserStatus(request.args["status"]))
    if request.args.get("department"):
        query = query.where(Exhibitor.departamento == request.args["department"])
    if request.args.get("municipality"):
        query = query.where(Exhibitor.municipio == request.args["municipality"])
    if request.args.get("document_type") in {item.value for item in DocumentType}:
        query = query.where(Exhibitor.tipo_documento == DocumentType(request.args["document_type"]))
    query = apply_created_dates(query, Exhibitor.created_at).order_by(Exhibitor.created_at.desc())
    rows = []
    for item in db.session.scalars(query.limit(MAX_REPORT_ROWS)):
        type_name = db.session.scalar(
            select(ExhibitorType.nombre)
            .join(ExhibitorTypeLink, ExhibitorTypeLink.type_id == ExhibitorType.id)
            .where(ExhibitorTypeLink.exhibitor_id == item.id)
        )
        rows.append({
        "nombre_comercial": item.nombre_comercial,
        "tipo_expositor": type_name,
        "nombre_tipo_expositor": item.nombre_tipo_expositor,
        "responsable": " ".join(filter(None, [item.nombre_responsable, item.apellido_paterno_responsable or item.apellido_responsable, item.apellido_materno_responsable])),
        "tipo_documento": item.tipo_documento,
        "numero_documento": item.numero_documento,
        "correo": item.correo,
        "whatsapp": item.telefono_whatsapp,
        "departamento": item.departamento,
        "municipio": item.municipio,
        "direccion": item.direccion,
        "estado": item.estado,
        "creado": item.created_at,
        })
    return rows


def fair_rows():
    query = select(Fair).where(Fair.deleted_at.is_(None))
    term = request.args.get("q", "").strip()
    if term:
        pattern = f"%{term}%"
        query = query.where(or_(Fair.nombre.ilike(pattern), Fair.lugar.ilike(pattern)))
    if request.args.get("status") in {item.value for item in FeriaStatus}:
        query = query.where(Fair.estado == FeriaStatus(request.args["status"]))
    if request.args.get("department"):
        query = query.where(Fair.departamento == request.args["department"])
    start, end = parse_date("date_from"), parse_date("date_to")
    if start:
        query = query.where(Fair.fecha_fin >= start)
    if end:
        query = query.where(Fair.fecha_inicio <= end)
    query = query.order_by(Fair.fecha_inicio.desc())
    return [{
        "nombre": item.nombre, "lugar": item.lugar, "departamento": item.departamento,
        "direccion": item.direccion,
        "fecha_inicio": item.fecha_inicio, "fecha_fin": item.fecha_fin,
        "estado": item.estado, "visible": item.visible_publicamente,
        "descripcion": item.descripcion, "creado": item.created_at,
    } for item in db.session.scalars(query.limit(MAX_REPORT_ROWS))]


def product_rows():
    query = (
        select(Product, Exhibitor, Category)
        .join(Exhibitor, Product.exhibitor_id == Exhibitor.id)
        .join(Category, Product.category_id == Category.id)
        .where(Product.deleted_at.is_(None))
    )
    term = request.args.get("q", "").strip()
    if term:
        pattern = f"%{term}%"
        query = query.where(or_(Product.nombre.ilike(pattern), Product.descripcion.ilike(pattern), Exhibitor.nombre_comercial.ilike(pattern)))
    if request.args.get("status") in {item.value for item in ProductStatus}:
        query = query.where(Product.estado == ProductStatus(request.args["status"]))
    exhibitor_id = parse_uuid("exhibitor_id")
    category_id = parse_uuid("category_id")
    if exhibitor_id:
        query = query.where(Product.exhibitor_id == exhibitor_id)
    if category_id:
        query = query.where(Product.category_id == category_id)
    query = apply_created_dates(query, Product.created_at).order_by(Product.created_at.desc())
    return [{
        "nombre": product.nombre, "expositor": exhibitor.nombre_comercial,
        "categoria": category.nombre, "descripcion": product.descripcion,
        "estado": product.estado,
        "origen": product.lugar_origen, "presentacion": product.presentacion,
        "creado": product.created_at,
    } for product, exhibitor, category in db.session.execute(query.limit(MAX_REPORT_ROWS))]


def category_rows():
    query = select(Category).where(Category.deleted_at.is_(None))
    term = request.args.get("q", "").strip()
    if term:
        query = query.where(or_(Category.nombre.ilike(f"%{term}%"), Category.descripcion.ilike(f"%{term}%")))
    if request.args.get("status") in {"active", "inactive"}:
        query = query.where(Category.estado.is_(request.args["status"] == "active"))
    query = apply_created_dates(query, Category.created_at).order_by(Category.nombre)
    return [{
        "nombre": item.nombre, "descripcion": item.descripcion, "estado": item.estado,
        "creado": item.created_at, "actualizado": item.updated_at,
    } for item in db.session.scalars(query.limit(MAX_REPORT_ROWS))]


def audit_rows():
    query = select(Audit, User).outerjoin(User, Audit.user_id == User.id)
    term = request.args.get("q", "").strip()
    if term:
        pattern = f"%{term}%"
        query = query.where(or_(Audit.accion.ilike(pattern), Audit.entidad.ilike(pattern), Audit.descripcion.ilike(pattern), User.username.ilike(pattern)))
    if request.args.get("action"):
        query = query.where(Audit.accion == request.args["action"])
    if request.args.get("entity"):
        query = query.where(Audit.entidad == request.args["entity"])
    user_id = parse_uuid("user_id")
    if user_id:
        query = query.where(Audit.user_id == user_id)
    query = apply_created_dates(query, Audit.created_at).order_by(Audit.created_at.desc())
    return [{
        "fecha": item.created_at, "usuario": user.username if user else "Sistema",
        "accion": item.accion.replace("_", " ").title(), "entidad": item.entidad,
        "descripcion": item.descripcion, "ip": item.ip_address,
    } for item, user in db.session.execute(query.limit(MAX_REPORT_ROWS))]


ROW_BUILDERS = {
    "administradores": administrator_rows,
    "expositores": exhibitor_rows,
    "ferias": fair_rows,
    "productos": product_rows,
    "categorias": category_rows,
    "auditoria": audit_rows,
}


def report_sections(resource):
    resources = list(ROW_BUILDERS) if resource == "general" else [resource]
    sections = []
    for item in resources:
        columns = selected_columns(item) if resource != "general" else list(REPORT_COLUMNS[item])
        sections.append((item, columns, ROW_BUILDERS[item]()))
    return sections


def build_xlsx(sections):
    workbook = Workbook()
    workbook.remove(workbook.active)
    header_fill = PatternFill("solid", fgColor="17324D")
    header_font = Font(color="FFFFFF", bold=True)
    for resource, columns, rows in sections:
        sheet = workbook.create_sheet(REPORT_TITLES[resource][:31])
        headers = [REPORT_COLUMNS[resource][column] for column in columns]
        sheet.append(headers)
        for cell in sheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        for row in rows:
            values = [display(row.get(column)) for column in columns]
            sheet.append([
                f"'{value}" if isinstance(value, str) and value.startswith(("=", "+", "-", "@")) else value
                for value in values
            ])
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        sheet.sheet_view.showGridLines = False
        for index, header in enumerate(headers, 1):
            values = [str(sheet.cell(row=row, column=index).value or "") for row in range(1, min(sheet.max_row, 200) + 1)]
            sheet.column_dimensions[get_column_letter(index)].width = min(45, max(12, len(header) + 2, *(len(value) + 2 for value in values)))
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output


def build_pdf(sections, generated_at):
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=landscape(A4), rightMargin=10 * mm, leftMargin=10 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
        title="Reporte de Ferias Productivas Bolivia",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#17324D"), fontSize=18)
    cell_style = ParagraphStyle("ReportCell", parent=styles["BodyText"], fontSize=6.5, leading=8)
    header_style = ParagraphStyle("ReportHeader", parent=cell_style, textColor=colors.white, alignment=TA_CENTER)
    story = []
    for section_index, (resource, columns, rows) in enumerate(sections):
        if section_index:
            story.append(PageBreak())
        story.append(Paragraph(f"Reporte de {REPORT_TITLES[resource]}", title_style))
        story.append(Paragraph(f"Generado: {generated_at.strftime('%d/%m/%Y %H:%M:%S')} · Registros: {len(rows)}", styles["Normal"]))
        story.append(Spacer(1, 5 * mm))
        headers = [Paragraph(REPORT_COLUMNS[resource][column], header_style) for column in columns]
        data = [headers]
        for row in rows:
            data.append([Paragraph(display(row.get(column)).replace("&", "&amp;").replace("<", "&lt;"), cell_style) for column in columns])
        if len(data) == 1:
            data.append([Paragraph("Sin registros para los filtros seleccionados", cell_style)] + [""] * (len(columns) - 1))
        available_width = landscape(A4)[0] - 20 * mm
        table = Table(data, repeatRows=1, colWidths=[available_width / len(columns)] * len(columns))
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
            ("GRID", (0, 0), (-1, -1), .3, colors.HexColor("#CBD5DF")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F8")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(table)
    document.build(story)
    output.seek(0)
    return output


@report_bp.get("/reports/options")
@roles(*ROLES_ADMINISTRACION_INSTITUCIONAL)
def report_options():
    actions = db.session.scalars(select(Audit.accion).distinct().order_by(Audit.accion)).all()
    entities = db.session.scalars(select(Audit.entidad).distinct().order_by(Audit.entidad)).all()
    return {
        "resources": [
            {"value": key, "label": title, "columns": [{"value": name, "label": label} for name, label in columns.items()]}
            for key, title in REPORT_TITLES.items() if key != "general"
            for columns in [REPORT_COLUMNS[key]]
        ],
        "actions": actions,
        "entities": entities,
    }


@report_bp.get("/reports/<resource>")
@roles(*ROLES_ADMINISTRACION_INSTITUCIONAL)
def download_report(resource):
    if resource not in {*ROW_BUILDERS, "general"}:
        return error("Tipo de reporte no válido", 404)
    report_format = request.args.get("format", "pdf").lower()
    if report_format not in {"pdf", "xlsx"}:
        return error("El formato debe ser PDF o Excel")
    try:
        sections = report_sections(resource)
    except ValueError as exc:
        return error(str(exc))
    generated_at = datetime.now(BOLIVIA_TZ)
    output = build_pdf(sections, generated_at) if report_format == "pdf" else build_xlsx(sections)
    extension = "pdf" if report_format == "pdf" else "xlsx"
    filename = f"reporte_{resource}_{generated_at.strftime('%Y-%m-%d_%H%M%S')}.{extension}"
    total = sum(len(rows) for _, _, rows in sections)
    audit("GENERAR_REPORTE", "Reporte", description=f"Reporte {resource} generado en {extension.upper()} con {total} registros")
    db.session.commit()
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf" if extension == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
