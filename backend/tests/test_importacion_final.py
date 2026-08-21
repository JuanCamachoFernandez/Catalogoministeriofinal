from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.exc import DataError

from app.extensiones import db
from app.esquemas.solicitudes_registro import optional_representative_name_validator
from app.fuentes_importacion import build_plan, clear_items, plan_sha256, sha
from app.importador_final import (
    dry_run_summary_text, execute_plan, media_validation_text, preflight_plan,
    safe_database_error, validate_plan_media,
)
from app.modelos import (
    FinalImportRun, FinalImportSourceRow, Product, ProductImage, ProductStatus, ProductiveUnit,
    RegistrationRequest, User,
)
from app.utilidades import bounded_slug
from app.servicios.archivos import MediaStageError


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


def valid_image_bytes():
    output = BytesIO()
    Image.new("RGB", (8, 8), "blue").save(output, format="PNG")
    return output.getvalue()


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
    reasons = plan["summary"]["pending_by_reason"]
    assert reasons == {"correo_responsable_invalido": 1, "representante_no_divisible": 1}
    assert plan["summary"]["errors"] == 0
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
    assert plan["summary"]["pending_by_reason"] == {"encabezado_no_encontrado": 1}
    assert plan["summary"]["errors"] == 0


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
        "detected": 3, "importable": 2, "draft": 1, "ambiguous": 0, "pending": 2,
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
    assert plan["summary"]["pending_rows"] == {
        "general": {"correo_responsable_invalido": [2]},
        "corrected": {},
    }
    output = dry_run_summary_text(plan["summary"])
    assert "correo_responsable_invalido -> filas [2]" in output
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


def test_plan_hash_is_deterministic_and_changes_with_source_data():
    first = build_plan(document([valid_row()]), document([]), "general", "corrected")
    second = build_plan(document([valid_row()]), document([]), "general", "corrected")
    changed_row = valid_row(description="Contenido diferente")
    changed = build_plan(document([changed_row]), document([]), "general", "corrected")
    assert first["plan_hash"] == second["plan_hash"] == plan_sha256(first)
    assert changed["plan_hash"] != first["plan_hash"]


def test_dry_run_prints_safe_classification_and_plan_hash(app, monkeypatch):
    general, corrected = document([valid_row()]), document([])

    class FakeGoogle:
        def __init__(self, _token):
            pass

        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

    monkeypatch.setattr("app.importador_final.GoogleSource", FakeGoogle)
    result = app.test_cli_runner().invoke(args=[
        "importar-datos-finales", "--sheet-general", "general",
        "--sheet-corregidos", "corrected", "--dry-run",
    ])
    expected = build_plan(general, corrected, "general", "corrected")["plan_hash"]
    assert result.exit_code == 0
    assert "UNIDADES" in result.output
    assert "PENDING BY REASON" in result.output
    assert result.output.strip().endswith(f"PLAN_SHA256: {expected}")
    assert "unidad@gmail.com" not in result.output


def test_plan_trace_preserves_original_corrected_product_and_image_rows():
    corrected = {"title": "corregidos", "worksheets": [
        {"title": "Unidades", "values": [["ID_UP", *HEADERS[:11]], ["UP-01", *valid_row()[:11]]]},
        {"title": "Productos", "values": [
            ["ID_UP", "ID_PRODUCTO", "NOMBRE_PRODUCTO", "DESCRIPCION", "PRECIO_REFERENCIA"],
            ["UP-01", "P-01", "Producto original", "Texto original", "19.90"],
        ]},
        {"title": "Imagenes", "values": [
            ["ID_PRODUCTO", "DRIVE_ID"], ["P-01", "abcdefghijklmnopqrstuv"],
        ]},
    ]}
    plan = build_plan(document([]), corrected, "general", "corrected")
    traced = {(row["worksheet"], row["row_number"]): row["data"] for row in plan["trace_rows"]}
    assert traced[("Productos", 2)]["DESCRIPCION"] == "Texto original"
    assert traced[("Productos", 2)]["PRECIO_REFERENCIA"] == "19.90"
    assert traced[("Imagenes", 2)]["DRIVE_ID"] == "abcdefghijklmnopqrstuv"


def test_commit_with_wrong_expected_hash_stops_before_database_writes(app, monkeypatch):
    general, corrected = document([valid_row()]), document([])

    class FakeGoogle:
        def __init__(self, _token):
            pass

        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

    monkeypatch.setattr("app.importador_final.GoogleSource", FakeGoogle)
    with app.app_context():
        result = app.test_cli_runner().invoke(args=[
            "importar-datos-finales", "--sheet-general", "general",
            "--sheet-corregidos", "corrected", "--commit",
            "--expect-plan-sha256", "0" * 64, "--confirm", "IMPORT-FINAL",
        ])
        assert result.exit_code != 0
        assert "PLAN_SHA256 no coincide" in result.output
        assert db.session.scalar(select(func.count()).select_from(FinalImportRun)) == 0
        assert db.session.scalar(select(func.count()).select_from(ProductiveUnit)) == 0


def test_structural_pending_is_preserved_without_blocking_commit(app):
    invalid = valid_row()
    invalid[3] = "correo-invalido"
    general, corrected = document([invalid]), document([])
    plan = build_plan(general, corrected, "general", "corrected")

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

    with app.app_context():
        result = execute_plan(plan, FakeGoogle())
        assert result["status"] == "COMPLETED"
        assert result["summary"]["units_structural_pending"] == 1
        assert result["summary"]["pending_records_preserved"] == 1
        assert db.session.scalar(select(func.count()).select_from(ProductiveUnit)) == 0
        trace = db.session.scalar(select(FinalImportSourceRow))
        assert trace.is_pending is True
        assert trace.pending_reasons == ["correo_responsable_invalido"]


def test_actual_plan_errors_still_block_commit_before_writes(app):
    general, corrected = document([valid_row()]), document([])
    plan = build_plan(general, corrected, "general", "corrected")
    plan["summary"]["errors"] = 1
    plan["plan_hash"] = plan_sha256(plan)

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

    with app.app_context(), pytest.raises(Exception, match="errores reales"):
        execute_plan(plan, FakeGoogle())
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(FinalImportRun)) == 0


def test_optional_unit_fields_import_as_empty_without_invented_values(app):
    row = valid_row()
    row[1], row[2], row[4], row[7], row[9], row[10] = "", "", "", "", "", ""
    general, corrected = document([row]), document([])
    plan = build_plan(general, corrected, "general", "corrected")
    assert plan["summary"]["unit_classification"] == {
        "importable_complete": 0, "importable_incomplete": 1, "structural_pending": 0,
    }

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

    with app.app_context():
        execute_plan(plan, FakeGoogle())
        unit = db.session.scalar(select(ProductiveUnit))
        user = db.session.scalar(select(User))
        product = db.session.scalar(select(Product))
        assert unit.razon_social == ""
        assert unit.nit is None
        assert unit.telefono_whatsapp == ""
        assert unit.direccion_fisica == ""
        assert unit.resena_comercial == ""
        assert unit.apellido_materno_representante == ""
        assert user.phone is None
        assert product.estado == ProductStatus.DRAFT


def test_pending_unit_does_not_prevent_other_units_from_importing(app):
    importable = valid_row(name="Unidad Importable")
    pending = valid_row(name="Unidad Pendiente")
    pending[2], pending[3] = "7654321", ""
    general, corrected = document([importable, pending]), document([])
    plan = build_plan(general, corrected, "general", "corrected")
    assert plan["summary"]["unit_classification"]["structural_pending"] == 1

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

    with app.app_context():
        result = execute_plan(plan, FakeGoogle())
        assert result["summary"]["units_created"] == 1
        assert result["summary"]["pending_records_preserved"] == 1
        assert db.session.scalar(select(func.count()).select_from(ProductiveUnit)) == 1


def test_preflight_reports_table_column_and_row_without_source_values(app):
    general, corrected = document([]), document([valid_row()])
    plan = build_plan(general, corrected, "general", "corrected")
    product = plan["units"][0]["products"][0]
    product["dimensions"] = "x" * 256
    product["presentation"] = "p" * 200
    plan["plan_hash"] = plan_sha256(plan)
    issues = preflight_plan(plan)
    assert any(
        issue["table"] == "productos" and issue["column"] == "dimensiones"
        and issue["reason"] == "value_too_long" and issue["actual_length"] == 256
        for issue in issues
    )
    # The legitimate 200-character presentation now fits both compatibility columns.
    assert not any(issue["column"] in {"presentacion", "presentacion_empaque"} for issue in issues)
    serialized = str(issues)
    assert "unidad@gmail.com" not in serialized and "Unidad Uno" not in serialized


def test_preflight_blocks_before_download_or_database_write(app):
    general, corrected = document([]), document([valid_row()])
    plan = build_plan(general, corrected, "general", "corrected")
    plan["units"][0]["products"][0]["stock"] = "9" * 256
    plan["plan_hash"] = plan_sha256(plan)

    class FakeGoogle:
        downloads = 0

        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

        def download(self, _file_id):
            self.downloads += 1

    google = FakeGoogle()
    with app.app_context(), pytest.raises(Exception, match="productos.capacidad_produccion_stock"):
        execute_plan(plan, google)
    with app.app_context():
        assert google.downloads == 0
        assert db.session.scalar(select(func.count()).select_from(FinalImportRun)) == 0


def test_data_error_diagnostic_is_sanitized(app, caplog):
    class Diagnostic:
        table_name = "productos"
        column_name = "presentacion"

    class OriginalError(Exception):
        sqlstate = "22001"
        diag = Diagnostic()

    error = DataError("INSERT with private data", {"email": "private@example.com"}, OriginalError())
    error._final_import_context = {
        "model": "Product", "table": "productos", "source": "GENERAL",
        "worksheet": "Respuestas", "row": 15,
    }
    with app.app_context():
        message = safe_database_error(error)
    assert "tabla=productos" in message
    assert "columna=presentacion" in message
    assert "sqlstate=22001" in message
    assert "value too long for varchar" in message
    assert "private@example.com" not in message and "private@example.com" not in caplog.text


def test_data_error_rolls_back_and_compensates_uploaded_images(app, monkeypatch):
    general, corrected = document([]), document([valid_row()])
    plan = build_plan(general, corrected, "general", "corrected")
    plan["units"][0]["products"][0]["images"] = ["abcdefghijklmnopqrstuv"]
    plan["plan_hash"] = plan_sha256(plan)
    deleted = []

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

        def download(self, _file_id):
            return "safe.png", BytesIO(b"image bytes")

    monkeypatch.setattr("app.importador_final.prepare_image", lambda *_args, **_kwargs: {
        "filename": "safe.webp", "stream": BytesIO(b"webp bytes"),
    })
    monkeypatch.setattr("app.importador_final.upload_prepared_to_cloudinary", lambda *_args, **_kwargs: {
        "filename": "safe.webp", "url": "https://res.cloudinary.com/example/image/upload/safe.webp",
        "public_id": "catalogo/productos/safe",
    })
    monkeypatch.setattr("app.importador_final.delete_cloudinary_upload", deleted.append)

    class Diagnostic:
        table_name = "productos"
        column_name = "presentacion"

    class OriginalError(Exception):
        sqlstate = "22001"
        diag = Diagnostic()

    def fail_after_upload(*_args, **_kwargs):
        raise DataError("private statement", {"private": "value"}, OriginalError())

    monkeypatch.setattr("app.importador_final.trace_entities", fail_after_upload)
    with app.app_context(), pytest.raises(Exception, match="cloudinary_compensation=1/1 failed=0"):
        execute_plan(plan, FakeGoogle())
    with app.app_context():
        assert deleted == ["catalogo/productos/safe"]
        assert db.session.scalar(select(func.count()).select_from(FinalImportRun)) == 0
        assert db.session.scalar(select(func.count()).select_from(ProductiveUnit)) == 0
        assert db.session.scalar(select(func.count()).select_from(Product)) == 0


def test_unit_header_matcher_never_uses_product_question_as_business_name():
    headers = [
        "Describa el nombre comercial del producto y sus principales caracteristicas",
        "Correo", "Telefono", "Nombres representante", "Apellido paterno", "Departamento",
    ]
    values = ["Texto descriptivo largo", "unidad@example.com", "71234567", "Ana", "Perez", "La Paz"]
    general = {"title": "general", "worksheets": [{"title": "Respuestas", "values": [headers, values]}]}
    plan = build_plan(general, document([]), "general", "corrected")
    assert plan["summary"]["unit_classification"]["structural_pending"] == 1
    assert plan["pending_units"][0]["reasons"] == [{"reason": "unidad_no_identificable"}]


def test_corrected_long_product_name_keeps_real_origin_and_fits_expanded_columns():
    long_name = "P" * 205
    corrected = {"title": "corregidos", "worksheets": [
        {"title": "Unidades", "values": [["ID_UP", *HEADERS[:11]], ["UP-01", *valid_row()[:11]]]},
        {"title": "Productos", "values": [
            ["ID_UP", "ID_PRODUCTO", "NOMBRE_PRODUCTO"], ["UP-01", "P-01", long_name],
        ]},
    ]}
    plan = build_plan(document([]), corrected, "general", "corrected")
    product = plan["units"][0]["products"][0]
    assert product["origin"]["worksheet"] == "Productos"
    assert product["origin"]["row_number"] == 2
    assert product["origin"]["field_headers"]["nombre"] == "NOMBRE_PRODUCTO"
    assert not any(issue["table"] == "productos" for issue in preflight_plan(plan))
    assert len(bounded_slug(product["name"])) <= 220


def test_oversized_optional_tiktok_is_omitted_but_preserved_in_trace():
    headers = HEADERS[:11] + ["TikTok"]
    oversized = "https://www.tiktok.com/@cuenta/" + "x" * 530
    general = {"title": "general", "worksheets": [{
        "title": "Respuestas", "values": [headers, valid_row()[:11] + [oversized]],
    }]}
    plan = build_plan(general, document([]), "general", "corrected")
    assert plan["units"][0]["unit"]["tiktok"] == ""
    assert plan["summary"]["warnings_by_reason"]["tiktok_url_invalido_omitido"] == 1
    assert plan["trace_rows"][0]["data"]["TikTok"] == oversized
    assert not any(issue["column"] == "tiktok_url" for issue in preflight_plan(plan))


def test_bounded_slug_is_deterministic_limited_and_collision_resistant():
    first_name = "Producto " + "muy largo " * 40 + "A"
    second_name = "Producto " + "muy largo " * 40 + "B"
    first = bounded_slug(first_name)
    assert first == bounded_slug(first_name)
    assert len(first) <= 220
    assert first != bounded_slug(second_name)


def test_logotipo_de_unidad_productiva_never_maps_to_business_name():
    headers = [
        "5.Activos Digitales y Contenido Multimedia 5.1. Logotipo de la Unidad Productiva",
        "Correo", "Telefono", "Nombres representante", "Apellido paterno", "Departamento",
    ]
    values = ["logo-drive-value", "unidad@example.com", "71234567", "Ana", "Perez", "La Paz"]
    general = {"title": "general", "worksheets": [{"title": "Respuestas", "values": [headers, values]}]}
    plan = build_plan(general, document([]), "general", "corrected")
    assert plan["summary"]["unit_classification"]["structural_pending"] == 1
    assert plan["pending_units"][0]["reasons"] == [{"reason": "unidad_no_identificable"}]
    mapping = plan["summary"]["field_header_mapping"]["nombre_comercial"]
    assert mapping == {"<NO ENCONTRADO>": 1}


def test_canonical_business_name_question_is_selected_explicitly():
    headers = [
        "1.1 Nombre comercial de la Unidad Productiva",
        "5.1 Logotipo de la Unidad Productiva",
        *HEADERS[1:11],
    ]
    values = ["Unidad Canonica", "logo-drive-value", *valid_row()[1:11]]
    general = {"title": "general", "worksheets": [{"title": "Respuestas", "values": [headers, values]}]}
    plan = build_plan(general, document([]), "general", "corrected")
    assert plan["units"][0]["unit"]["business_name"] == "Unidad Canonica"
    mapping = plan["summary"]["field_header_mapping"]["nombre_comercial"]
    assert mapping == {"1.1 Nombre comercial de la Unidad Productiva": 1}


def test_combined_social_network_header_is_not_used_as_tiktok():
    headers = HEADERS[:11] + ["Facebook, Instagram y TikTok", "Enlace de TikTok"]
    values = valid_row()[:11] + ["texto combinado", "https://www.tiktok.com/@cuenta"]
    general = {"title": "general", "worksheets": [{"title": "Respuestas", "values": [headers, values]}]}
    plan = build_plan(general, document([]), "general", "corrected")
    assert plan["units"][0]["unit"]["tiktok"] == "https://www.tiktok.com/@cuenta"
    mapping = plan["summary"]["field_header_mapping"]["tiktok_url"]
    assert mapping == {"Enlace de TikTok": 1}
    assert "tiktok_url_invalido_omitido" not in plan["summary"]["warnings_by_reason"]


def test_accepted_ambiguities_do_not_block_and_original_row_is_preserved(app):
    headers = HEADERS[:11] + ["Productos", "Fotografias de los productos"]
    source = valid_row()[:11] + [
        "Producto uno, Producto dos",
        "https://drive.google.com/open?id=abcdefghijklmnopqrstuv",
    ]
    general = {"title": "general", "worksheets": [{"title": "Respuestas", "values": [headers, source]}]}
    corrected = document([])
    plan = build_plan(general, corrected, "general", "corrected")
    assert plan["summary"]["warning_severity"]["blocking"] == 0
    for warning in plan["warnings"]:
        if warning["reason"] in {"producto_general_ambiguo", "fotografias_generales_ambiguas"}:
            warning["severity"] = "blocking"  # Compatibility with plans generated by the prior release.
    plan["plan_hash"] = plan_sha256(plan)

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

    with app.app_context():
        result = execute_plan(plan, FakeGoogle())
        assert result["status"] == "COMPLETED"
        trace = db.session.scalar(select(FinalImportSourceRow).where(FinalImportSourceRow.is_ambiguous.is_(True)))
        assert trace is not None
        assert trace.source_data["Productos"] == "Producto uno, Producto dos"
        assert trace.source_data["Fotografias de los productos"].endswith("abcdefghijklmnopqrstuv")
        assert result["summary"]["ambiguous_records_preserved"] == 1


def test_import_never_sends_temporary_credentials(app, monkeypatch):
    general, corrected = document([]), document([valid_row()])
    plan = build_plan(general, corrected, "general", "corrected")
    calls = []
    monkeypatch.setattr(
        "app.servicios.servicio_correo.BrevoEmailService.send_temporary_credentials",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

    with app.app_context():
        result = execute_plan(plan, FakeGoogle())
        assert result["summary"]["emails_sent"] == 0
        assert calls == []


def plan_with_one_product_image():
    corrected = {"title": "corregidos", "worksheets": [
        {"title": "Unidades", "values": [["ID_UP", *HEADERS[:11]], ["UP-01", *valid_row()[:11]]]},
        {"title": "Productos", "values": [
            ["ID_UP", "ID_PRODUCTO", "NOMBRE_PRODUCTO"], ["UP-01", "P-01", "Producto A"],
        ]},
        {"title": "Imagenes", "values": [
            ["ID_PRODUCTO", "DRIVE_ID"], ["P-01", "abcdefghijklmnopqrstuv"],
        ]},
    ]}
    general = document([])
    return build_plan(general, corrected, "general", "corrected"), general, corrected


def test_corrupt_image_is_pending_and_does_not_abort_batch(app):
    plan, general, corrected = plan_with_one_product_image()

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

        def download(self, _file_id):
            return "corrupt.png", BytesIO(b"not an image")

    with app.app_context():
        result = execute_plan(plan, FakeGoogle())
        assert result["status"] == "COMPLETED"
        assert result["summary"]["media_errors"] == 1
        assert db.session.scalar(select(func.count()).select_from(ProductImage)) == 0
        image_row = db.session.scalar(select(FinalImportSourceRow).where(
            FinalImportSourceRow.worksheet == "Imagenes"
        ))
        assert image_row.is_pending is True
        assert image_row.warnings[0]["stage"] == "image_open"


def test_drive_download_failure_does_not_abort_batch(app):
    plan, general, corrected = plan_with_one_product_image()

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

        def download(self, _file_id):
            raise ValueError("operation failed")

    with app.app_context():
        result = execute_plan(plan, FakeGoogle())
        assert result["status"] == "COMPLETED"
        assert result["summary"]["media_errors"] == 1
        assert db.session.scalar(select(func.count()).select_from(Product)) == 1
        assert db.session.scalar(select(func.count()).select_from(ProductImage)) == 0


def test_webp_conversion_failure_does_not_abort_batch(app, monkeypatch):
    plan, general, corrected = plan_with_one_product_image()

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

        def download(self, _file_id):
            return "valid.png", BytesIO(valid_image_bytes())

    monkeypatch.setattr("app.importador_final.prepare_image", lambda *_args, **_kwargs: (
        _ for _ in ()
    ).throw(MediaStageError("image_convert", "No fue posible convertir la imagen a WEBP",
                            origin_type="OSError")))
    with app.app_context():
        result = execute_plan(plan, FakeGoogle())
        assert result["status"] == "COMPLETED"
        assert result["summary"]["media_errors"] == 1
        assert db.session.scalar(select(func.count()).select_from(ProductImage)) == 0


def test_individual_cloudinary_failure_creates_no_false_image_url(app, monkeypatch):
    plan, general, corrected = plan_with_one_product_image()

    class FakeGoogle:
        def spreadsheet(self, sheet_id):
            return general if sheet_id == "general" else corrected

        def download(self, _file_id):
            return "valid.png", BytesIO(valid_image_bytes())

    monkeypatch.setattr("app.importador_final.upload_prepared_to_cloudinary", lambda *_args, **_kwargs: (
        _ for _ in ()
    ).throw(MediaStageError("cloudinary_upload", "operation failed", origin_type="ValueError")))
    with app.app_context():
        result = execute_plan(plan, FakeGoogle())
        assert result["status"] == "COMPLETED"
        assert result["summary"]["media_errors"] == 1
        assert db.session.scalar(select(func.count()).select_from(ProductImage)) == 0


def test_read_only_media_validation_uses_production_normalization_without_upload(app, monkeypatch):
    plan, _general, _corrected = plan_with_one_product_image()
    uploads = []

    class FakeGoogle:
        def download(self, _file_id):
            return "valid.png", BytesIO(valid_image_bytes())

    monkeypatch.setattr("app.importador_final.upload_prepared_to_cloudinary", uploads.append)
    with app.app_context():
        summary = validate_plan_media(plan, FakeGoogle())
        output = media_validation_text(summary)
        assert summary == {
            "logos_reviewed": 0, "product_images_reviewed": 1, "valid": 1,
            "invalid": 0, "errors": [],
        }
        assert "MEDIA VALIDATION" in output and "invalidas: 0" in output
        assert uploads == []
        assert db.session.scalar(select(func.count()).select_from(FinalImportRun)) == 0


def test_media_validation_includes_ambiguous_general_photos(app):
    headers = HEADERS[:11] + ["Productos", "Fotografias de los productos"]
    photo_ids = ["abcdefghijklmnopqrstuv", "bcdefghijklmnopqrstuvw"]
    row = valid_row()[:11] + [
        "Producto uno, Producto dos",
        ",".join(f"https://drive.google.com/open?id={item}" for item in photo_ids),
    ]
    plan = build_plan(
        {"title": "general", "worksheets": [{"title": "Respuestas", "values": [headers, row]}]},
        document([]), "general", "corrected",
    )

    class FakeGoogle:
        def download(self, _file_id):
            return "valid.png", BytesIO(valid_image_bytes())

    with app.app_context():
        summary = validate_plan_media(plan, FakeGoogle())
        assert summary["product_images_reviewed"] == 2
        assert summary["valid"] == 2
