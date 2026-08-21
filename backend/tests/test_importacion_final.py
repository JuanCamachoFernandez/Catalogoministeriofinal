import pytest
from sqlalchemy import func, select

from app.extensiones import db
from app.esquemas.solicitudes_registro import optional_representative_name_validator
from app.fuentes_importacion import build_plan, clear_items, sha
from app.importador_final import dry_run_summary_text, execute_plan
from app.modelos import FinalImportRun, Product, ProductStatus, ProductiveUnit, RegistrationRequest, User


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
        "PRECIO_REFERENCIA", "PRESENTACION", "CAPACIDAD_PRODUCCION_STOCK", "MATERIA_PRIMA",
    ]
    products = [
        ["UP-01", "P-01", "Producto completo", "Descripción", "25,50", "Caja", "100", "Miel"],
        ["UP-01", "P-02", "Producto borrador", "", "", "", "", ""],
        ["UP-99", "P-03", "Producto huérfano", "Descripción", "10", "Unidad", "20", "Miel"],
        ["UP-01", "P-04", "", "Descripción sin nombre", "10", "Unidad", "20", "Miel"],
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


def test_real_corrected_email_relations_and_composite_product_image_key():
    unit_headers = ["correo_electronico", *HEADERS[:3], *HEADERS[4:11]]
    first = [" unidad1@example.com ", *valid_row()[:3], *valid_row()[4:11]]
    second_source = valid_row(name="Unidad Dos")
    second_source[1:5] = ["Unidad Dos SRL", "7654321", "unidad2@example.com", "71234567"]
    second = ["UNIDAD2@EXAMPLE.COM", *second_source[:3], *second_source[4:11]]
    product_headers = [
        "correo_electronico_unidad", "categoria_nombre", "nombre_comercial", "descripcion_tecnica",
        "materia_prima", "dimensiones", "colores_disponibles", "certificaciones",
        "presentacion_empaque", "precio_referencia", "capacidad_produccion_stock", "estado_deseado",
    ]
    product_rows = [
        ["UNIDAD1@EXAMPLE.COM", "Alimentos", "Producto Compartido", "Descripción uno", "Miel", "", "", "", "Frasco", "20", "50", "AVAILABLE"],
        [" unidad2@example.com ", "Alimentos", "Producto Compartido", "Descripción dos", "Miel", "", "", "", "Frasco", "30", "60", "AVAILABLE"],
    ]
    corrected = {"title": "corregidos", "worksheets": [
        {"title": "Unidades", "values": [unit_headers, first, second]},
        {"title": "SectoresUnidad", "values": [
            ["correo_electronico", "sector_nombre", "detalle_otro"],
            ["unidad1@example.com", "Alimentos", ""], ["unidad2@example.com", "Alimentos", ""],
        ]},
        {"title": "Productos", "values": [product_headers, *product_rows]},
        {"title": "ImagenesProducto", "values": [
            ["correo_electronico_unidad", "nombre_comercial_producto", "orden", "url_imagen", "texto_alternativo", "es_portada"],
            ["unidad1@example.com", "Producto Compartido", "1", "https://drive.google.com/open?id=abcdefghijklmnopqrstuv", "", "TRUE"],
            ["UNIDAD2@EXAMPLE.COM", "producto compartido", "1", "https://drive.google.com/open?id=zyxwvutsrqponmlkjihgfe", "", "TRUE"],
        ]},
    ]}
    plan = build_plan(document([]), corrected, "general", "corrected")
    assert plan["summary"]["product_sources"]["corrected"]["without_unit"] == 0
    assert plan["summary"]["product_sources"]["corrected"]["detected"] == 2
    assert plan["summary"]["image_sources"]["corrected"]["assigned"] == 2
    assert plan["summary"]["image_sources"]["corrected"]["without_product"] == 0
    assert plan["summary"]["sector_sources"]["corrected"] == {
        "rows_read": 2, "associated": 2, "without_unit": 0,
    }
    images_by_email = {
        group["unit"]["email"]: group["products"][0]["images"] for group in plan["units"]
    }
    assert images_by_email["unidad1@example.com"] == ["abcdefghijklmnopqrstuv"]
    assert images_by_email["unidad2@example.com"] == ["zyxwvutsrqponmlkjihgfe"]


def test_general_product_photos_extracts_multiple_comma_separated_drive_urls():
    headers = [
        "Nombre de la Unidad Productiva", "Razón social", "Correo electrónico", "Número de WhatsApp",
        "Nombre completo del representante legal", "Departamento", "Dirección física", "Reseña comercial",
        "Productos que elabora",
        "5.2. Fotografías de los Productos ( 3 fotos por producto): enlaces de Google Drive",
    ]
    photo_ids = ["abcdefghijklmnopqrstuv", "bcdefghijklmnopqrstuvw", "cdefghijklmnopqrstuvwx"]
    values = [
        "Unidad Fotos", "Unidad Fotos SRL", "fotos@example.com", "71234567", "Ana Pérez Mamani",
        "La Paz", "Calle 3", "Producción local", "Miel",
        ",\n".join(f"https://drive.google.com/open?id={identifier}" for identifier in photo_ids),
    ]
    general = {"title": "general", "worksheets": [{"title": "Respuestas", "values": [headers, values]}]}
    plan = build_plan(general, document([]), "general", "corrected")
    assert plan["summary"]["image_sources"]["general"] == {
        "logos_detected": 0, "photos_detected": 3, "assignable": 3, "ambiguous": 0,
    }
    assert plan["units"][0]["products"][0]["images"] == photo_ids


def test_two_part_representative_is_valid_and_never_invents_maternal_surname(app):
    optional_representative_name_validator("")
    headers = [
        "Nombre de la Unidad Productiva", "Razón social", "Correo electrónico", "Número de WhatsApp",
        "Nombre completo del representante legal", "Departamento", "Dirección física", "Reseña comercial",
    ]
    values = [
        "Unidad Dos Apellidos", "Unidad Dos Apellidos SRL", "dos-apellidos@example.com", "71234567",
        "Bárbara Lima", "La Paz", "Calle 4", "Producción local",
    ]
    general = {"title": "general", "worksheets": [{"title": "Respuestas", "values": [headers, values]}]}
    corrected = document([])
    plan = build_plan(general, corrected, "general", "corrected")
    assert plan["summary"]["unique_units"] == 1
    assert "representante_no_divisible" not in plan["summary"]["errors_by_reason"]
    assert plan["units"][0]["unit"]["first_names"] == "Bárbara"
    assert plan["units"][0]["unit"]["paternal_name"] == "Lima"
    assert plan["units"][0]["unit"]["maternal_name"] == ""

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

    with app.app_context():
        result = execute_plan(plan, FakeGoogle())
        assert result["status"] == "COMPLETED"
        assert db.session.scalar(select(User)).apellido_materno == ""
        assert db.session.scalar(select(ProductiveUnit)).apellido_materno_representante == ""
        assert db.session.scalar(select(RegistrationRequest)).apellido_materno_representante == ""
