import pytest
from marshmallow import ValidationError

from app.esquemas.productos import (
    ProductiveProductCreateSchema,
    ProductiveProductUpdateSchema,
)


VALID_PRODUCT = {
    "nombre_comercial": "Miel Andina 500 g",
    "descripcion_tecnica": "Miel natural, presentación 500 g; lote N.º 12/2026.",
    "materia_prima": "Miel 100",
    "dimensiones": "20 x 15 cm",
    "colores_disponibles": "Dorado ámbar",
    "certificaciones": "SENASAG N.º 123/2026",
    "presentacion_empaque": "Caja 12 unidades, pack/bolsa - promoción",
    "precio_referencia": "55.00",
    "capacidad_produccion_stock": "100",
}


def test_producto_productivo_acepta_datos_validos_y_texto_mixto():
    loaded = ProductiveProductCreateSchema().load(VALID_PRODUCT)

    assert loaded["nombre_comercial"] == "Miel Andina 454gr"
    assert loaded["capacidad_produccion_stock"] == "100"
    assert loaded["certificaciones"] == "SENASAG N.º 123/2026"
    assert loaded["presentacion_empaque"] == "Caja 12 unidades, pack/bolsa - promoción"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("nombre_comercial", "Miel @ Andina"),
        ("materia_prima", "Miel #1"),
        ("presentacion_empaque", "Caja x 12 + bolsas"),
        ("colores_disponibles", "Rojo 2"),
        ("capacidad_produccion_stock", "100 unidades"),
    ],
)
def test_producto_productivo_rechaza_formatos_invalidos_al_crear(field, value):
    payload = {**VALID_PRODUCT, field: value}

    with pytest.raises(ValidationError) as error:
        ProductiveProductCreateSchema().load(payload)

    assert field in error.value.messages


def test_producto_productivo_aplica_las_mismas_reglas_al_editar():
    with pytest.raises(ValidationError) as error:
        ProductiveProductUpdateSchema().load(
            {"capacidad_produccion_stock": "25 unidades"}
        )

    assert "capacidad_produccion_stock" in error.value.messages
