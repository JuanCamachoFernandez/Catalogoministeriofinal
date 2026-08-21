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


def test_relational_product_audit_reads_aliases_and_keeps_incomplete_products_as_draft():
    unit_headers = ["ID_UP", *HEADERS[:11]]
    unit = ["UP-01", *valid_row()[:11]]
    product_headers = [
        "ID_UP", "ID_PRODUCTO", "NOMBRE_PRODUCTO", "DESCRIPCION",
        "PRECIO_REFERENCIA", "PRESENTACION", "CAPACIDAD_PRODUCCION_STOCK",
    ]
    products = [
        ["UP-01", "P-01", "Producto completo", "Descripción", "25,50", "Caja", "100"],
        ["UP-01", "P-02", "Producto borrador", "", "", "", ""],
        ["UP-99", "P-03", "Producto huérfano", "Descripción", "10", "Unidad", "20"],
        ["UP-01", "P-04", "", "Descripción sin nombre", "10", "Unidad", "20"],
    ]
    corrected = {"title": "corregidos", "worksheets": [
        {"title": "Unidades", "values": [unit_headers, unit]},
        {"title": "Productos", "values": [["CATÁLOGO DE PRODUCTOS"], product_headers, *products]},
        {"title": "Imagenes", "values": [
            ["ID_PRODUCTO", "DRIVE_ID"],
            ["P-01", "abcdefghijklmnopqrstuv"],
            ["NO-EXISTE", "zyxwvutsrqponmlkjihgfe"],
        ]},
    ]}
    plan = build_plan(document([]), corrected, "general", "corrected")
    products_summary = plan["summary"]["product_sources"]["corrected"]
    assert products_summary == {
        "rows_read": 4, "detected": 3, "valid": 1, "draft": 1,
        "invalid": 1, "without_unit": 1,
    }
    assert plan["summary"]["product_sources"]["total"] == {
        "detected": 3, "importable": 2, "draft": 1, "ambiguous": 0,
    }
    imported = {product["name"]: product for product in plan["units"][0]["products"]}
    assert imported["Producto completo"]["price"] == "25.50"
    assert imported["Producto completo"]["presentation"] == "Caja"
    assert imported["Producto completo"]["stock"] == "100"
    assert imported["Producto borrador"]["images"] == []
    assert plan["summary"]["image_sources"]["corrected"]["assigned"] == 1
    assert plan["summary"]["image_sources"]["corrected"]["without_product"] == 1


def test_dry_run_lists_only_source_rows_for_unit_errors():
    row = valid_row()
    row[3], row[4] = "correo-malo", "123"
    plan = build_plan(document([row]), document([]), "general", "corrected")
    assert plan["summary"]["error_rows"] == {
        "general": {"correo_invalido": [2], "telefono_invalido": [2]},
        "corrected": {},
    }
    output = dry_run_summary_text(plan["summary"])
    assert "correo_invalido -> filas [2]" in output
    assert "telefono_invalido -> filas [2]" in output
    assert row[0] not in output and row[3] not in output and row[4] not in output
    assert "WARNINGS BY REASON" in output
    assert "PRODUCTOS CORREGIDOS" in output
    assert "IMÁGENES CORREGIDOS" in output


def test_execute_plan_preserves_structured_product_fields_in_draft(app):
    corrected = {"title": "corregidos", "worksheets": [
        {"title": "Unidades", "values": [["ID_UP", *HEADERS[:11]], ["UP-01", *valid_row()[:11]]]},
        {"title": "Productos", "values": [[
            "ID_UP", "ID_PRODUCTO", "NOMBRE_PRODUCTO", "DESCRIPCION",
            "PRECIO_REFERENCIA", "PRESENTACION", "CAPACIDAD_PRODUCCION_STOCK",
        ], ["UP-01", "P-01", "Producto A", "Descripción", "25.50", "Caja", "100"]]},
    ]}
    general = document([])
    plan = build_plan(general, corrected, "general", "corrected")

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

    with app.app_context():
        result = execute_plan(plan, FakeGoogle())
        assert result["status"] == "COMPLETED"
        product = db.session.scalar(select(Product))
        assert product.estado == ProductStatus.DRAFT
        assert str(product.precio_referencia) == "25.50"
        assert product.presentacion_empaque == "Caja"
        assert product.capacidad_produccion_stock == "100"
