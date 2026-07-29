from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.controllers.common import audit_description
from app.models import (
    Audit,
    Fair,
    FeriaStatus,
    ProductiveUnit,
    ProductiveUnitStatus,
    RegistrationRequest,
    RegistrationStatus,
    Role,
    User,
    UserStatus,
)
from app.models.fair import bolivia_today


PASSWORD = "Temporal2026!"


def test_descripciones_de_auditoria_no_exponen_nombres_tecnicos():
    assert audit_description("CAMBIAR_ESTADO", "ProductiveUnit") == (
        "Cambio de estado de Unidad Productiva"
    )
    assert audit_description("RESTAURAR", "ProductiveUnit") == (
        "Restauración de Unidad Productiva"
    )
    assert audit_description("CREAR_SOLICITUD", "RegistrationRequest") == (
        "Creación de solicitud de registro"
    )


def create_user(username, role):
    user = User(
        username=username,
        email=f"{username}@gmail.com",
        role=role,
        first_name=username.title(),
        last_name="Pruebas",
        status=UserStatus.ACTIVE,
        must_change_password=False,
    )
    user.set_password(PASSWORD)
    db.session.add(user)
    db.session.flush()
    return user


def create_registration(index, department, created_at=None):
    item = RegistrationRequest(
        nombre_comercial=f"Unidad {index}",
        razon_social=f"Unidad {index} SRL",
        nombres_representante="Ana",
        apellido_paterno_representante="Quispe",
        apellido_materno_representante="Mamani",
        departamento=department,
        direccion_fisica="Calle de prueba",
        telefono_whatsapp=f"7123456{index}",
        correo_electronico=f"unidad{index}@gmail.com",
        resena_comercial="Producción nacional",
        estado=RegistrationStatus.APPROVED,
    )
    if created_at:
        item.created_at = created_at
    db.session.add(item)
    db.session.flush()
    return item


def create_unit(index, department):
    user = create_user(f"unidad{index}", Role.PRODUCTIVE_UNIT_RESPONSIBLE)
    registration = create_registration(index, department)
    unit = ProductiveUnit(
        user_id=user.id,
        registration_request_id=registration.id,
        nombre_comercial=registration.nombre_comercial,
        razon_social=registration.razon_social,
        nombres_representante=registration.nombres_representante,
        apellido_paterno_representante=registration.apellido_paterno_representante,
        apellido_materno_representante=registration.apellido_materno_representante,
        departamento=department,
        direccion_fisica=registration.direccion_fisica,
        telefono_whatsapp=registration.telefono_whatsapp,
        correo_electronico=registration.correo_electronico,
        resena_comercial=registration.resena_comercial,
        estado=ProductiveUnitStatus.ACTIVE,
        fecha_aprobacion=datetime.now(timezone.utc),
    )
    db.session.add(unit)


def test_dashboard_muestra_indicadores_y_oculta_eventos_rutinarios(app, client):
    with app.app_context():
        admin = create_user("administrador", Role.SUPERADMIN)
        create_unit(1, "La Paz")
        create_unit(2, "Cochabamba")
        create_registration(
            9,
            "Santa Cruz",
            datetime.now(timezone.utc) - timedelta(days=40),
        )
        fair = Fair(
            nombre="Feria Productiva",
            slug="feria-productiva",
            lugar="Campo Ferial",
            ubicacion="Campo Ferial, La Paz",
            departamento="La Paz",
            fecha_inicio=bolivia_today() + timedelta(days=5),
            fecha_fin=bolivia_today() + timedelta(days=7),
            estado=FeriaStatus.DRAFT,
            visible_publicamente=False,
            created_by=admin.id,
        )
        db.session.add_all(
            [
                fair,
                Audit(
                    user_id=admin.id,
                    accion="CERRAR_SESION",
                    entidad="Usuario",
                    entidad_id=admin.id,
                    descripcion="Sesión cerrada",
                ),
                Audit(
                    user_id=admin.id,
                    accion="REAUTENTICAR",
                    entidad="Usuario",
                    entidad_id=admin.id,
                    descripcion="Sesión desbloqueada",
                ),
                Audit(
                    user_id=admin.id,
                    accion="APROBAR_SOLICITUD",
                    entidad="RegistrationRequest",
                    descripcion="Solicitud aprobada",
                ),
            ]
        )
        db.session.commit()

    login = client.post(
        "/api/auth/login",
        json={"login": "administrador", "password": PASSWORD},
    )
    response = client.get(
        "/api/admin/dashboard",
        headers={"Authorization": f"Bearer {login.json['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json["stats"]["solicitudes_ultimos_30_dias"] == 2
    assert response.json["proxima_feria"]["nombre"] == "Feria Productiva"
    assert response.json["proxima_feria"]["dias_restantes"] == 5
    assert response.json["unidades_por_departamento"] == [
        {"departamento": "Cochabamba", "cantidad": 1},
        {"departamento": "La Paz", "cantidad": 1},
    ]
    assert [item["accion"] for item in response.json["recent_audits"]] == [
        "APROBAR_SOLICITUD"
    ]
