import pytest
from sqlalchemy import func, select

from app.extensiones import db
from app.fuentes_importacion import build_plan, clear_items, sha
from app.importador_final import execute_plan
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
