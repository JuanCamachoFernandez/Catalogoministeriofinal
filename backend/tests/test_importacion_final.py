import pytest
from sqlalchemy import func, select

from app.extensiones import db
from app.fuentes_importacion import build_plan, clear_items, sha
from app.importador_final import dry_run_summary_text, execute_plan
from app.modelos import FinalImportRun, Product, ProductStatus, ProductiveUnit, User


HEADERS = [
    "Nombre comercial", "Razon social", "NIT", "Correo", "Telefono",
    "Nombres representante", "Apellido paterno", "Apellido materno", "Departamento",
    "Direccion", "Resena comercial", "Producto 1", "Producto 1 descripcion",
]


def document(rows):
    return {"title": "fuente", "worksheets": [{"title": "Respuestas", "values": [HEADERS, *rows]}]}


def valid_row(name="Unidad Uno", description="Descripción corregida"):
    return [name, "Unidad Uno SRL", "1234567", "unidad@gmail.com", "76543210", "Ana",
            "Pérez", "Mamani", "La Paz", "Calle 1", "Producción local", "Producto A", description]


def test_conservative_parser_never_splits_commas():
    assert clear_items("pan, queso, miel") == []
    assert clear_items("1. Pan 2. Queso") == ["Pan", "Queso"]


def test_corrected_source_has_priority_and_duplicate_product_is_merged():
    corrected, general = document([valid_row(description="Corregida")]), document([valid_row(description="General")])
    plan = build_plan(general, corrected, "general", "corrected")
    assert plan["summary"]["unique_units"] == 1
    assert plan["summary"]["merged_units"] == 1
    assert len(plan["units"][0]["products"]) == 1
    assert plan["units"][0]["products"][0]["description"] == "Corregida"


def test_conflicting_identifiers_are_reported():
    first = valid_row(name="Mismo Nombre")
    second = valid_row(name="Mismo Nombre")
    second[2], second[3] = "9999999", "otro@gmail.com"
    plan = build_plan(document([second]), document([first]), "general", "corrected")
    assert plan["summary"]["possible_duplicates"] == 1


def test_relational_corrected_template_preserves_product_image_assignment():
    unit_headers, unit_values = HEADERS[:11], valid_row()[:11]
    corrected = {"title": "corregidos", "worksheets": [
        {"title": "Unidades", "values": [unit_headers, unit_values]},
        {"title": "Productos", "values": [["Nombre comercial", "Codigo producto", "Nombre producto", "Descripcion"],
                                             ["Unidad Uno", "P-1", "Producto A", "Descripción explícita"]]},
        {"title": "Imagenes", "values": [["Codigo producto", "Drive ID"],
                                           ["P-1", "abcdefghijklmnopqrstuv"]]},
    ]}
    plan = build_plan(document([]), corrected, "general", "corrected")
    assert plan["summary"]["unique_units"] == 1
    assert plan["units"][0]["products"][0]["images"] == ["abcdefghijklmnopqrstuv"]


def test_execute_plan_is_idempotent_and_creates_draft_without_images(app):
    general, corrected = document([]), document([valid_row()])
    plan = build_plan(general, corrected, "general", "corrected")

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

    with app.app_context():
        result = execute_plan(plan, FakeGoogle())
        assert result["status"] == "COMPLETED"
        assert db.session.scalar(select(func.count()).select_from(User)) == 1
        assert db.session.scalar(select(func.count()).select_from(ProductiveUnit)) == 1
        product = db.session.scalar(select(Product))
        assert product.estado == ProductStatus.DRAFT
        assert db.session.scalar(select(func.count()).select_from(FinalImportRun)) == 1
        with pytest.raises(Exception, match="ya fue ejecutado"):
            execute_plan(plan, FakeGoogle())


def test_long_form_headers_title_row_and_full_representative_are_supported():
    headers = [
        "Nombre de la Unidad Productiva", "Razón social de la unidad productiva",
        "Número de NIT (si corresponde)", "Correo electrónico de contacto",
        "Número de WhatsApp", "Nombre completo del representante legal",
        "¿En qué departamento se encuentra?", "Dirección física de la unidad",
        "Breve reseña comercial", "Productos que elabora",
    ]
    values = [
        "Unidad Dos", "Unidad Dos SRL", "", "unidad2@example.com", "+591 71234567",
        "Ana María Pérez Mamani", "Potosí", "Calle 2", "Producción artesanal", "Miel",
    ]
    general = {"title": "general", "worksheets": [{"title": "Respuestas", "values": [
        ["REGISTRO DE UNIDADES PRODUCTIVAS"], headers, values,
    ]}]}
    plan = build_plan(general, document([]), "general", "corrected")
    assert plan["summary"]["unique_units"] == 1
    assert plan["units"][0]["unit"]["first_names"] == "Ana María"
    assert plan["units"][0]["unit"]["paternal_name"] == "Pérez"
    assert plan["units"][0]["unit"]["maternal_name"] == "Mamani"
    assert plan["units"][0]["unit"]["nit"] == ""
    assert plan["units"][0]["unit"]["phone"] == "71234567"
    assert plan["units"][0]["products"][0]["name"] == "Miel"
    assert plan["units"][0]["products"][0]["description"] == ""
    assert plan["summary"]["sources"]["general"] == {"rows_read": 1, "valid": 1, "invalid": 0}


def test_relational_units_do_not_depend_on_products_sheet():
    corrected = {"title": "corregidos", "worksheets": [
        {"title": "Unidades", "values": [HEADERS[:11], valid_row()[:11]]},
        {"title": "Sectores", "values": [["Codigo unidad", "Sector"], ["Unidad Uno", "Textiles"]]},
        {"title": "Imagenes", "values": [["Codigo producto", "Drive ID"]]},
    ]}
    plan = build_plan(document([]), corrected, "general", "corrected")
    assert plan["summary"]["unique_units"] == 1
    assert plan["summary"]["products_detected"] == 0
    assert plan["units"][0]["unit"]["sectors"] == ["Textiles"]
    assert plan["summary"]["sources"]["corrected"] == {"rows_read": 1, "valid": 1, "invalid": 0}


def test_trailing_sheet_blanks_do_not_shift_columns():
    row = valid_row()
    row[2] = ""
    plan = build_plan(document([row]), document([]), "general", "corrected")
    assert plan["summary"]["unique_units"] == 1
    assert plan["units"][0]["unit"]["email"] == "unidad@gmail.com"
    assert plan["units"][0]["unit"]["nit"] == ""


def test_invalid_reasons_are_aggregated_without_personal_data_in_cli_output():
    row = valid_row()
    row[3], row[4], row[5], row[6], row[7] = "correo-malo", "123", "Solo", "", ""
    plan = build_plan(document([row]), document([]), "general", "corrected")
    reasons = plan["summary"]["errors_by_reason"]
    assert reasons == {"correo_invalido": 1, "representante_no_divisible": 1, "telefono_invalido": 1}
    output = dry_run_summary_text(plan["summary"])
    assert "ERRORS BY REASON" in output
    assert "GENERAL:" in output and "CORREGIDOS:" in output
    for private_value in (row[0], row[3], row[4], row[5]):
        assert private_value not in output


def test_unrecognized_header_has_a_specific_reason():
    unknown = {"title": "fuente", "worksheets": [{"title": "Respuestas", "values": [
        ["Columna A", "Columna B"], ["valor", "otro valor"],
    ]}]}
    plan = build_plan(unknown, document([]), "general", "corrected")
    assert plan["summary"]["errors_by_reason"] == {"encabezado_no_encontrado": 1}
