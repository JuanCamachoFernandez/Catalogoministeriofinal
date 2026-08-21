from datetime import datetime, timezone
from urllib.parse import unquote
from uuid import UUID
from io import BytesIO
from zoneinfo import ZoneInfo

from PIL import Image
from sqlalchemy import select

from app.extensiones import db
from app.modelos import (
    Product,
    ProductiveSector,
    ProductiveUnit,
    RegistrationRequest,
    Role,
    SectorStatus,
    UnitSector,
    User,
    UserStatus,
)


def _admin(client):
    user = User(
        username="admin.dominio",
        email="admin.dominio@gmail.com",
        role=Role.ADMIN,
        first_name="Admin",
        last_name="Dominio",
        status=UserStatus.ACTIVE,
        must_change_password=False,
    )
    user.set_password("AdminDominio2026!")
    db.session.add(user)
    db.session.commit()
    response = client.post(
        "/api/auth/login",
        json={"login": user.username, "password": "AdminDominio2026!"},
    )
    return {"Authorization": f"Bearer {response.json['access_token']}"}


def _png():
    stream = BytesIO()
    Image.new("RGB", (8, 8), "green").save(stream, format="PNG")
    stream.seek(0)
    return stream


def _upload_request_logo(client):
    response = client.post(
        "/api/registration-requests/logo",
        data={"file": (_png(), "logo.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    return response.json["logo_url"]


def _upload_request_image(client, filename):
    response = client.post(
        "/api/registration-requests/products/image",
        data={"file": (_png(), filename)},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    return response.json["imagen_url"]


def _registration_payload(client, sector_id):
    payload = {
        "nombre_comercial": "Manos Andinas",
        "razon_social": "Manos Andinas SRL",
        "nit": "123456789",
        "nombres_representante": "Ana María",
        "apellido_paterno_representante": "Quispe",
        "apellido_materno_representante": "Mamani",
        "departamento": "La Paz",
        "direccion_fisica": "Calle 1",
        "telefono_whatsapp": "76543210",
        "correo_electronico": "ana@manos.bo",
        "resena_comercial": "Artesanía boliviana",
        "logo_url": _upload_request_logo(client),
        "sectores": [{"productive_sector_id": str(sector_id)}],
    }
    payload["productos"] = [
        {
            "nombre_comercial": f"Producto de prueba {index + 1}",
            "descripcion_tecnica": "Descripción de prueba",
            "precio_referencia": "10.00",
            "imagen_url": _upload_request_image(client, f"producto-{index + 1}.png"),
        }
        for index in range(3)
    ]
    return payload


def test_admin_puede_registrar_una_unidad_sin_logo_ni_productos(app, client):
    with app.app_context():
        sector = ProductiveSector(nombre="Manufactura", es_otro=False)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    admin_headers = _admin(client)
    response = client.post(
        "/api/admin/productive-units",
        headers=admin_headers,
        json={
            "nombre_comercial": "Tejidos del Altiplano",
            "razon_social": "Tejidos del Altiplano SRL",
            "nit": "987654321",
            "nombres_representante": "Lucía",
            "apellido_paterno_representante": "Mamani",
            "apellido_materno_representante": "Quispe",
            "departamento": "La Paz",
            "direccion_fisica": "Calle 2",
            "telefono_whatsapp": "76543210",
            "correo_electronico": "lucia@tejidos.bo",
            "resena_comercial": "Tejidos artesanales de alpaca",
            "sectores": [{"productive_sector_id": str(sector_id)}],
        },
    )

    assert response.status_code == 201
    detail = client.get(
        f"/api/admin/productive-units/{response.json['id']}",
        headers=admin_headers,
    )
    assert detail.status_code == 200
    assert detail.json["productos"] == []
    with app.app_context():
        unit = db.session.get(ProductiveUnit, UUID(response.json["id"]))
        assert unit.logo_url is None
        assert unit.estado.value == "ACTIVE"
        assert db.session.scalar(select(UnitSector.id).where(UnitSector.productive_unit_id == unit.id))
        user = db.session.get(User, unit.user_id)
        assert user.must_change_password is True


def test_solicitud_valida_identificadores_con_separadores_y_e_final_en_pro_bolivia(
    app, client
):
    with app.app_context():
        sector = ProductiveSector(nombre="Manufactura", es_otro=False)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    for invalid_nit in ("1234", "1234567890123", "ABC123456", "12A34"):
        payload = _registration_payload(client, sector_id)
        payload["nit"] = invalid_nit
        response = client.post("/api/registration-requests", json=payload)
        assert response.status_code == 400

    for invalid_seprec in ("1234", "1234567890123", "SEPREC123", "12B34"):
        payload = _registration_payload(client, sector_id)
        payload["registro_seprec"] = invalid_seprec
        response = client.post("/api/registration-requests", json=payload)
        assert response.status_code == 400

    for invalid_pro_bolivia in ("1234", "1234567890123", "PROBOL123", "22E7630", "227630EX"):
        payload = _registration_payload(client, sector_id)
        payload["registro_pro_bolivia"] = invalid_pro_bolivia
        response = client.post("/api/registration-requests", json=payload)
        assert response.status_code == 400

    valid_payload = _registration_payload(client, sector_id)
    valid_payload["nit"] = "12_345/67-89"
    valid_payload["registro_seprec"] = "12/345_67-89"
    valid_payload["registro_pro_bolivia"] = "228770-E"
    response = client.post("/api/registration-requests", json=valid_payload)
    assert response.status_code == 201

    valid_payload = _registration_payload(client, sector_id)
    valid_payload["correo_electronico"] = "ana.probolivia@manos.bo"
    valid_payload["nit"] = "12345"
    valid_payload["registro_seprec"] = "12345"
    valid_payload["registro_pro_bolivia"] = "227630E"
    response = client.post("/api/registration-requests", json=valid_payload)
    assert response.status_code == 201


def test_solicitud_requiere_nombres_y_apellido_paterno_y_admite_materno_vacio(app, client):
    with app.app_context():
        sector = ProductiveSector(nombre="Madera", es_otro=False)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    representative_fields = (
        "nombres_representante",
        "apellido_paterno_representante",
    )
    for field in representative_fields:
        payload = _registration_payload(client, sector_id)
        payload.pop(field)
        response = client.post("/api/registration-requests", json=payload)
        assert response.status_code == 400

        payload = _registration_payload(client, sector_id)
        payload[field] = ""
        response = client.post("/api/registration-requests", json=payload)
        assert response.status_code == 400

        payload = _registration_payload(client, sector_id)
        payload[field] = "   "
        response = client.post("/api/registration-requests", json=payload)
        assert response.status_code == 400

    payload = _registration_payload(client, sector_id)
    payload.pop("apellido_materno_representante")
    assert client.post("/api/registration-requests", json=payload).status_code == 400

    payload = _registration_payload(client, sector_id)
    payload["apellido_materno_representante"] = ""
    assert client.post("/api/registration-requests", json=payload).status_code == 201

    payload = _registration_payload(client, sector_id)
    payload["correo_electronico"] = "materno-espacios@example.com"
    payload["apellido_materno_representante"] = "   "
    assert client.post("/api/registration-requests", json=payload).status_code == 400


def test_solicitud_valida_nombres_telefono_boliviano_y_correo(app, client):
    with app.app_context():
        sector = ProductiveSector(nombre="Cerámica", es_otro=False)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    representative_fields = (
        "nombres_representante",
        "apellido_paterno_representante",
        "apellido_materno_representante",
    )
    for field in representative_fields:
        for invalid_name in ("Ana2", "Quispe!", "123456"):
            payload = _registration_payload(client, sector_id)
            payload[field] = invalid_name
            response = client.post("/api/registration-requests", json=payload)
            assert response.status_code == 400

    for invalid_phone in (
        "7123456",
        "712345678",
        "51234567",
        "71-234567",
        "+59171234567",
    ):
        payload = _registration_payload(client, sector_id)
        payload["telefono_whatsapp"] = invalid_phone
        response = client.post("/api/registration-requests", json=payload)
        assert response.status_code == 400

    for invalid_email in ("ana", "ana@", "@manos.bo", "ana@manos", "ana manos@manos.bo"):
        payload = _registration_payload(client, sector_id)
        payload["correo_electronico"] = invalid_email
        response = client.post("/api/registration-requests", json=payload)
        assert response.status_code == 400

    valid_payload = _registration_payload(client, sector_id)
    valid_payload["nombres_representante"] = "Ana María"
    valid_payload["apellido_paterno_representante"] = "D'Angelo"
    valid_payload["apellido_materno_representante"] = "Pérez-López"
    response = client.post("/api/registration-requests", json=valid_payload)
    assert response.status_code == 201


def test_solicitud_valida_urls_de_redes_sociales(app, client):
    with app.app_context():
        sector = ProductiveSector(nombre="Joyería", es_otro=False)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    invalid_social_urls = (
        ("facebook_url", "facebook.com/mi.unidad"),
        ("facebook_url", "https://instagram.com/mi.unidad"),
        ("instagram_url", "http://instagram.com/mi.unidad"),
        ("instagram_url", "https://facebook.com/mi.unidad"),
        ("tiktok_url", "https://tiktok.com/mi.unidad"),
        ("tiktok_url", "https://example.com/@mi.unidad"),
    )
    for field, invalid_url in invalid_social_urls:
        payload = _registration_payload(client, sector_id)
        payload[field] = invalid_url
        response = client.post("/api/registration-requests", json=payload)
        assert response.status_code == 400

    valid_payload = _registration_payload(client, sector_id)
    valid_payload.update(
        {
            "facebook_url": "https://facebook.com/mi.unidad",
            "instagram_url": "https://instagram.com/mi.unidad",
            "tiktok_url": "https://tiktok.com/@mi.unidad",
        }
    )
    response = client.post("/api/registration-requests", json=valid_payload)
    assert response.status_code == 201


def test_administracion_lista_sectores_activos_e_inactivos(app, client):
    with app.app_context():
        headers = _admin(client)
        active = ProductiveSector(nombre="Alimentos", es_otro=False)
        inactive = ProductiveSector(
            nombre="Textiles", es_otro=False, estado=SectorStatus.INACTIVE
        )
        db.session.add_all([active, inactive])
        db.session.commit()

    response = client.get("/api/admin/productive-sectors", headers=headers)
    assert response.status_code == 200
    assert {item["nombre"] for item in response.json["items"]} == {
        "Alimentos",
        "Textiles",
    }
    filtered = client.get(
        "/api/admin/productive-sectors?estado=INACTIVE", headers=headers
    )
    assert [item["nombre"] for item in filtered.json["items"]] == ["Textiles"]


def test_catalogo_lista_varias_ferias_simultaneas(app, client):
    with app.app_context():
        admin_headers = _admin(client)
    today = datetime.now(ZoneInfo("America/La_Paz")).date().isoformat()
    created_ids = []
    for name, location in (
        ("Feria Productiva Central", "La Paz"),
        ("Feria Productiva Regional", "El Alto"),
    ):
        response = client.post(
            "/api/admin/fairs",
            headers=admin_headers,
            json={
                "nombre": name,
                "ubicacion": location,
                "fecha_inicio": today,
                "fecha_fin": today,
            },
        )
        assert response.status_code == 201
        created_ids.append(response.json["id"])

    public = client.get("/api/public/fairs/active")
    assert public.status_code == 200
    assert public.json["active"] is True
    assert {item["id"] for item in public.json["items"]} == set(created_ids)


def test_solicitud_aprobacion_y_credenciales_temporales(app, client, monkeypatch):
    monkeypatch.setattr(
        "app.rutas.solicitudes_registro._temporary_password",
        lambda: "TemporalUnidad2026!",
    )
    with app.app_context():
        headers = _admin(client)
        sector = ProductiveSector(nombre="Artesanía", es_otro=False)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    response = client.post(
        "/api/registration-requests", json=_registration_payload(client, sector_id)
    )
    assert response.status_code == 201
    request_id = response.json["id"]
    duplicate = client.post(
        "/api/registration-requests", json=_registration_payload(client, sector_id)
    )
    assert duplicate.status_code == 409

    approved = client.post(
        f"/api/admin/registration-requests/{request_id}/approve",
        headers=headers,
        json={},
    )
    assert approved.status_code == 200
    assert approved.json["estado"] == "APPROVED"
    assert approved.json["nombre_representante"] == "Ana María Quispe Mamani"
    assert "temporary_password" not in approved.json

    with app.app_context():
        responsible = db.session.scalar(
            db.select(User).where(User.email == "ana@manos.bo")
        )
        assert responsible.first_name == "Ana María"
        assert responsible.apellido_paterno == "Quispe"
        assert responsible.apellido_materno == "Mamani"

    login = client.post(
        "/api/auth/login",
        json={"login": "ana@manos.bo", "password": "TemporalUnidad2026!"},
    )
    assert login.status_code == 200
    assert login.json["refresh_token"]
    assert login.json["user"]["must_change_password"] is True
    blocked = client.get(
        "/api/productive-unit/profile",
        headers={"Authorization": f"Bearer {login.json['access_token']}"},
    )
    assert blocked.status_code == 403

    changed = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {login.json['access_token']}"},
        json={
            "current_password": "TemporalUnidad2026!",
            "new_password": "DefinitivaUnidad2026!",
        },
    )
    assert changed.status_code == 200
    login = client.post(
        "/api/auth/login",
        json={"login": "ana@manos.bo", "password": "DefinitivaUnidad2026!"},
    )
    unit_headers = {"Authorization": f"Bearer {login.json['access_token']}"}
    with app.app_context():
        another_sector = ProductiveSector(nombre="Alimentos", es_otro=False)
        db.session.add(another_sector)
        db.session.commit()
        another_sector_id = another_sector.id

    replaced = client.put(
        "/api/productive-unit/sectors",
        headers=unit_headers,
        json={"sectores": [{"productive_sector_id": str(another_sector_id)}]},
    )
    assert replaced.status_code == 200
    with app.app_context():
        old_link = db.session.scalar(
            db.select(UnitSector).where(UnitSector.productive_sector_id == sector_id)
        )
        assert old_link.estado == SectorStatus.INACTIVE
        old_link_id = old_link.id

    restored = client.put(
        "/api/productive-unit/sectors",
        headers=unit_headers,
        json={"sectores": [{"productive_sector_id": str(sector_id)}]},
    )
    assert restored.status_code == 200
    with app.app_context():
        old_link = db.session.get(UnitSector, old_link_id)
        assert old_link.estado == SectorStatus.ACTIVE


def test_admin_puede_reenviar_credenciales_desde_detalle_unidad(app, client, monkeypatch):
    monkeypatch.setattr(
        "app.rutas.unidades_productivas._temporary_password",
        lambda: "TemporalUnidad2026!",
    )
    monkeypatch.setattr(
        "app.rutas.solicitudes_registro.BrevoEmailService.send_temporary_credentials",
        lambda *args, **kwargs: {"sent": False},
    )
    with app.app_context():
        headers = _admin(client)
        sector = ProductiveSector(nombre="Artesania", es_otro=False)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    created = client.post(
        "/api/admin/productive-units",
        headers=headers,
        json={
            "nombre_comercial": "Tejidos del Altiplano",
            "razon_social": "Tejidos del Altiplano SRL",
            "nit": "987654321",
            "nombres_representante": "Lucia",
            "apellido_paterno_representante": "Mamani",
            "apellido_materno_representante": "Quispe",
            "departamento": "La Paz",
            "direccion_fisica": "Calle 2",
            "telefono_whatsapp": "76543210",
            "correo_electronico": "lucia@tejidos.bo",
            "resena_comercial": "Tejidos artesanales de alpaca",
            "sectores": [{"productive_sector_id": str(sector_id)}],
        },
    )
    assert created.status_code == 201
    unit_id = created.json["id"]

    first_login = client.post(
        "/api/auth/login",
        json={"login": "lucia@tejidos.bo", "password": "TemporalUnidad2026!"},
    )
    assert first_login.status_code == 200

    changed = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {first_login.json['access_token']}"},
        json={
            "current_password": "TemporalUnidad2026!",
            "new_password": "DefinitivaUnidad2026!",
        },
    )
    assert changed.status_code == 200

    monkeypatch.setattr(
        "app.rutas.unidades_productivas._temporary_password",
        lambda: "ReenvioUnidad2026!",
    )
    resent = client.post(
        f"/api/admin/productive-units/{unit_id}/resend-credentials",
        headers=headers,
    )
    assert resent.status_code == 200
    assert resent.json["message"] == "Credenciales regeneradas"

    old_login = client.post(
        "/api/auth/login",
        json={"login": "lucia@tejidos.bo", "password": "DefinitivaUnidad2026!"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login",
        json={"login": "lucia@tejidos.bo", "password": "ReenvioUnidad2026!"},
    )
    assert new_login.status_code == 200
    assert new_login.json["user"]["must_change_password"] is True


def test_catalogo_deriva_todos_los_productos_de_la_unidad(app, client, monkeypatch):
    monkeypatch.setattr(
        "app.rutas.solicitudes_registro._temporary_password",
        lambda: "TemporalUnidad2026!",
    )
    with app.app_context():
        admin_headers = _admin(client)
        sector = ProductiveSector(nombre="Textiles", es_otro=False)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id
    requested = client.post("/api/registration-requests", json=_registration_payload(client, sector_id))
    request_id = requested.json["id"]
    client.post(f"/api/admin/registration-requests/{request_id}/approve", headers=admin_headers, json={})
    temporary_login = client.post("/api/auth/login", json={"login": "ana@manos.bo", "password": "TemporalUnidad2026!"})
    changed = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {temporary_login.json['access_token']}"},
        json={"current_password": "TemporalUnidad2026!", "new_password": "DefinitivaUnidad2026!"},
    )
    assert changed.status_code == 200
    login = client.post("/api/auth/login", json={"login": "ana@manos.bo", "password": "DefinitivaUnidad2026!"})
    unit_headers = {"Authorization": f"Bearer {login.json['access_token']}"}
    own_products = client.get("/api/productive-unit/products", headers=unit_headers)
    assert own_products.status_code == 200
    product_ids = [item["id"] for item in own_products.json["items"]]
    assert len(product_ids) == 3
    for number, product_id in enumerate(product_ids):
        for image_number in range(2):
            uploaded = client.post(
                f"/api/productive-unit/products/{product_id}/images",
                headers=unit_headers,
                data={
                    "file": (_png(), f"producto-{number}-{image_number}.png"),
                    "alt_text": f"Vista {image_number}",
                    "is_cover": "false",
                },
                content_type="multipart/form-data",
            )
            assert uploaded.status_code == 201
        published = client.patch(
            f"/api/productive-unit/products/{product_id}/status",
            headers=unit_headers,
            json={"estado": "AVAILABLE"},
        )
        assert published.status_code == 200

    today = datetime.now(ZoneInfo("America/La_Paz")).date().isoformat()
    fair = client.post(
        "/api/admin/fairs",
        headers=admin_headers,
        json={"nombre": "Feria vigente", "ubicacion": "La Paz", "fecha_inicio": today, "fecha_fin": today},
    )
    assert fair.status_code == 201
    profile = client.get("/api/productive-unit/profile", headers=unit_headers)
    unit_id = profile.json["id"]
    participation = client.post(
        f"/api/admin/fairs/{fair.json['id']}/participations",
        headers=admin_headers,
        json={"productive_unit_id": unit_id},
    )
    assert participation.status_code == 201
    assert participation.json["estado"] == "AUTHORIZED"
    public_products = client.get("/api/public/products")
    assert public_products.status_code == 200
    assert public_products.json["pagination"]["total"] == 3
    active_fairs = client.get("/api/public/fairs/active")
    assert active_fairs.status_code == 200
    assert active_fairs.json["active"] is True
    assert [item["id"] for item in active_fairs.json["items"]] == [fair.json["id"]]
    public_units = client.get(
        "/api/public/productive-units", query_string={"fair_id": fair.json["id"]}
    )
    assert public_units.status_code == 200
    assert public_units.json["pagination"]["total"] == 1
    public_unit = client.get(
        f"/api/public/productive-units/{unit_id}",
        query_string={"fair_id": fair.json["id"]},
    )
    assert public_unit.status_code == 200
    assert len(public_unit.json["productos"]) == 3
    whatsapp = client.post(
        "/api/public/whatsapp",
        json={
            "fair_id": fair.json["id"],
            "items": [{"product_id": product_ids[0], "quantity": 2}],
        },
    )
    assert whatsapp.status_code == 200
    assert whatsapp.json["url"].startswith("https://wa.me/591")
    whatsapp_message = unquote(whatsapp.json["url"].split("?text=", 1)[1])
    assert "Feria vigente" in whatsapp_message
    selected_product_name = next(
        item["nombre_comercial"]
        for item in public_unit.json["productos"]
        if item["id"] == product_ids[0]
    )
    assert f"{selected_product_name} — Cantidad: 2" in whatsapp_message

    base_product = {
        "descripcion_tecnica": "Descripción",
        "materia_prima": "Lana",
        "presentacion_empaque": "Unidad",
        "precio_referencia": "10.00",
        "capacidad_produccion_stock": "10",
    }
    for number in (4, 5):
        extra = client.post(
            "/api/productive-unit/products",
            headers=unit_headers,
            json={"nombre_comercial": f"Producto {number}", **base_product},
        )
        assert extra.status_code == 201
    last_created = None
    for number in range(6, 16):
        last_created = client.post(
            "/api/productive-unit/products",
            headers=unit_headers,
            json={"nombre_comercial": f"Producto {number}", **base_product},
        )
        assert last_created.status_code == 201
    over_limit = client.post(
        "/api/productive-unit/products",
        headers=unit_headers,
        json={"nombre_comercial": "Producto 16", **base_product},
    )
    assert over_limit.status_code == 409
    assert "máximo 15 productos" in over_limit.json["error"]

    deleted_product_id = last_created.json["id"]
    deleted = client.delete(
        f"/api/productive-unit/products/{deleted_product_id}",
        headers=unit_headers,
    )
    assert deleted.status_code == 204
    with app.app_context():
        assert db.session.get(Product, UUID(deleted_product_id)) is None
    replacement = client.post(
        "/api/productive-unit/products",
        headers=unit_headers,
        json={"nombre_comercial": "Producto de reemplazo", **base_product},
    )
    assert replacement.status_code == 201

    revoked = client.post(
        f"/api/admin/fairs/{fair.json['id']}/participations/{participation.json['id']}/revoke",
        headers=admin_headers,
    )
    assert revoked.status_code == 200
    assert client.get("/api/public/products").json["pagination"]["total"] == 0
    reauthorized = client.post(
        f"/api/admin/fairs/{fair.json['id']}/participations/{participation.json['id']}/authorize",
        headers=admin_headers,
    )
    assert reauthorized.status_code == 200
    retired = client.patch(
        f"/api/productive-unit/products/{product_ids[0]}/status",
        headers=unit_headers,
        json={"estado": "RETIRED"},
    )
    assert retired.status_code == 200
    # Participation history remains AUTHORIZED, but the complete unit disappears
    # dynamically when it drops below three publishable products.
    assert client.get("/api/public/products").json["pagination"]["total"] == 0


def test_participacion_nueva_queda_pendiente_si_la_unidad_no_cumple_reglas(app, client):
    with app.app_context():
        sector = ProductiveSector(nombre="Metalurgia", es_otro=False)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    admin_headers = _admin(client)
    unit = client.post(
        "/api/admin/productive-units",
        headers=admin_headers,
        json={
            "nombre_comercial": "Unidad Pendiente Feria",
            "razon_social": "Unidad Pendiente Feria SRL",
            "nit": "999111222",
            "nombres_representante": "Mariela",
            "apellido_paterno_representante": "Lopez",
            "apellido_materno_representante": "Quisbert",
            "departamento": "La Paz",
            "direccion_fisica": "Av. Siempre Viva 123",
            "telefono_whatsapp": "70011122",
            "correo_electronico": "pendiente.feria@gmail.com",
            "resena_comercial": "Unidad creada sin productos publicables para validar pendiente.",
            "sectores": [{"productive_sector_id": str(sector_id)}],
        },
    )
    assert unit.status_code == 201

    today = datetime.now(ZoneInfo("America/La_Paz")).date().isoformat()
    fair = client.post(
        "/api/admin/fairs",
        headers=admin_headers,
        json={
            "nombre": "Feria pendiente por reglas",
            "ubicacion": "La Paz",
            "fecha_inicio": today,
            "fecha_fin": today,
        },
    )
    assert fair.status_code == 201

    participation = client.post(
        f"/api/admin/fairs/{fair.json['id']}/participations",
        headers=admin_headers,
        json={"productive_unit_id": unit.json["id"]},
    )
    assert participation.status_code == 201
    assert participation.json["estado"] == "PENDING"

    authorize = client.post(
        f"/api/admin/fairs/{fair.json['id']}/participations/{participation.json['id']}/authorize",
        headers=admin_headers,
    )
    assert authorize.status_code == 409
    assert "al menos tres productos publicables" in authorize.json["error"]


def test_unidad_revocada_vuelve_a_poder_asignarse(app, client):
    with app.app_context():
        sector = ProductiveSector(nombre="Vidrio", es_otro=False)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    admin_headers = _admin(client)
    unit = client.post(
        "/api/admin/productive-units",
        headers=admin_headers,
        json={
            "nombre_comercial": "Unidad Reasignable",
            "razon_social": "Unidad Reasignable SRL",
            "nit": "999333444",
            "nombres_representante": "Paola",
            "apellido_paterno_representante": "Rojas",
            "apellido_materno_representante": "Mendoza",
            "departamento": "La Paz",
            "direccion_fisica": "Zona Sur 456",
            "telefono_whatsapp": "70033344",
            "correo_electronico": "reasignable.feria@gmail.com",
            "resena_comercial": "Unidad para validar revocación y nueva asignación.",
            "sectores": [{"productive_sector_id": str(sector_id)}],
        },
    )
    assert unit.status_code == 201

    today = datetime.now(ZoneInfo("America/La_Paz")).date().isoformat()
    fair = client.post(
        "/api/admin/fairs",
        headers=admin_headers,
        json={
            "nombre": "Feria de reasignación",
            "ubicacion": "La Paz",
            "fecha_inicio": today,
            "fecha_fin": today,
        },
    )
    assert fair.status_code == 201

    first = client.post(
        f"/api/admin/fairs/{fair.json['id']}/participations",
        headers=admin_headers,
        json={"productive_unit_id": unit.json["id"]},
    )
    assert first.status_code == 201
    assert first.json["estado"] == "PENDING"

    revoked = client.post(
        f"/api/admin/fairs/{fair.json['id']}/participations/{first.json['id']}/revoke",
        headers=admin_headers,
    )
    assert revoked.status_code == 200

    second = client.post(
        f"/api/admin/fairs/{fair.json['id']}/participations",
        headers=admin_headers,
        json={"productive_unit_id": unit.json["id"]},
    )
    assert second.status_code == 200
    assert second.json["id"] == first.json["id"]
    assert second.json["estado"] == "PENDING"


def test_admin_lista_solicitudes_filtra_por_rango_de_fechas(app, client):
    with app.app_context():
        headers = _admin(client)
        sector = ProductiveSector(nombre="Ceramica", es_otro=False)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    first = client.post("/api/registration-requests", json=_registration_payload(client, sector_id))
    second_payload = _registration_payload(client, sector_id)
    second_payload["correo_electronico"] = "otra@manos.bo"
    second_payload["nit"] = "987654321"
    second_payload["nombre_comercial"] = "Ceramica Andina"
    second_payload["razon_social"] = "Ceramica Andina SRL"
    second = client.post("/api/registration-requests", json=second_payload)

    assert first.status_code == 201
    assert second.status_code == 201

    with app.app_context():
        first_item = db.session.get(RegistrationRequest, UUID(first.json["id"]))
        second_item = db.session.get(RegistrationRequest, UUID(second.json["id"]))
        first_item.created_at = datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
        second_item.created_at = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)
        db.session.commit()

    filtered = client.get(
        "/api/admin/registration-requests?date_from=2026-07-20&date_to=2026-07-27",
        headers=headers,
    )

    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json["items"]] == [second.json["id"]]
