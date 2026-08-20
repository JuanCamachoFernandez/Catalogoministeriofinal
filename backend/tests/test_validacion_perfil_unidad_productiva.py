import pytest
from marshmallow import ValidationError

from app.esquemas.solicitudes_registro import RegistrationRequestSchema
from app.esquemas.unidades_productivas import (
    AdminProductiveUnitCreateSchema,
    ProductiveUnitUpdateSchema,
)


VALID_PROFILE = {
    "nombre_comercial": "Sabores del Valle 2026",
    "razon_social": "Sabores del Valle SRL",
    "nombres_representante": "María Elena",
    "apellido_paterno_representante": "Quispe",
    "apellido_materno_representante": "Mamani",
    "departamento": "Cochabamba",
    "direccion_fisica": "Zona Central, avenida Bolivia N.º 120",
    "telefono_whatsapp": "71234567",
    "correo_electronico": "contacto@empresa.com",
    "facebook_url": "https://facebook.com/miunidad",
    "instagram_url": "https://instagram.com/miunidad",
    "tiktok_url": "https://tiktok.com/@miunidad",
    "resena_comercial": "Elaboramos productos locales desde 2020.",
}


def test_perfil_productivo_acepta_datos_validos():
    loaded = ProductiveUnitUpdateSchema().load(VALID_PROFILE)

    assert loaded["departamento"] == "Cochabamba"
    assert loaded["telefono_whatsapp"] == "71234567"
    assert loaded["correo_electronico"] == "contacto@empresa.com"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("nit", "12-345/67_89"),
        ("registro_seprec", "12/345-67_89"),
        ("registro_pro_bolivia", "228770-E"),
        ("registro_pro_bolivia", "227630E"),
    ],
)
def test_perfil_productivo_acepta_identificadores_con_formato_legacy(field, value):
    loaded = ProductiveUnitUpdateSchema().load({field: value})

    assert loaded[field] == value


@pytest.mark.parametrize(
    "schema",
    [
        RegistrationRequestSchema(),
        AdminProductiveUnitCreateSchema(),
        ProductiveUnitUpdateSchema(),
    ],
)
def test_nombre_comercial_acepta_signos_visibles_en_todos_los_flujos(schema):
    loaded = schema.load(
        {"nombre_comercial": "Sabores & Valle S.R.L. #1 (@Centro)"},
        partial=True,
    )

    assert loaded["nombre_comercial"] == "Sabores & Valle S.R.L. #1 (@Centro)"


@pytest.mark.parametrize("value", ["   ", "Sabores\nValle", "Sabores\tValle"])
def test_nombre_comercial_rechaza_vacios_y_caracteres_de_control(value):
    with pytest.raises(ValidationError):
        ProductiveUnitUpdateSchema().load({"nombre_comercial": value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("nombre_comercial", "Sabores\nValle"),
        ("razon_social", "Sabores & Valle"),
        ("nombres_representante", "María 2"),
        ("apellido_paterno_representante", "Quispe1"),
        ("apellido_materno_representante", "Mamani_"),
        ("departamento", "Otro"),
        ("telefono_whatsapp", "7123456"),
        ("telefono_whatsapp", "59171234567"),
        ("correo_electronico", "correo-invalido"),
        ("nit", "12A34"),
        ("registro_seprec", "12B34"),
        ("registro_pro_bolivia", "22E7630"),
        ("registro_pro_bolivia", "227630EX"),
        ("facebook_url", "facebook.com/miunidad"),
        ("instagram_url", "mi perfil"),
        ("tiktok_url", "@miunidad"),
    ],
)
def test_perfil_productivo_rechaza_formatos_invalidos(field, value):
    with pytest.raises(ValidationError) as error:
        ProductiveUnitUpdateSchema().load({field: value})

    assert field in error.value.messages
