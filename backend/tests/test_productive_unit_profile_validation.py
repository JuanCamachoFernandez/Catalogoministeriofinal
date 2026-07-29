import pytest
from marshmallow import ValidationError

from app.views.productive_unit_view import ProductiveUnitUpdateSchema


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
        ("nombre_comercial", "Sabores @ Valle"),
        ("razon_social", "Sabores & Valle"),
        ("nombres_representante", "María 2"),
        ("apellido_paterno_representante", "Quispe1"),
        ("apellido_materno_representante", "Mamani_"),
        ("departamento", "Otro"),
        ("telefono_whatsapp", "7123456"),
        ("telefono_whatsapp", "59171234567"),
        ("correo_electronico", "correo-invalido"),
        ("facebook_url", "facebook.com/miunidad"),
        ("instagram_url", "mi perfil"),
        ("tiktok_url", "@miunidad"),
    ],
)
def test_perfil_productivo_rechaza_formatos_invalidos(field, value):
    with pytest.raises(ValidationError) as error:
        ProductiveUnitUpdateSchema().load({field: value})

    assert field in error.value.messages
