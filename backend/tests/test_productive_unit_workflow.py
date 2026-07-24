from datetime import datetime
from urllib.parse import unquote
from io import BytesIO
from zoneinfo import ZoneInfo

from PIL import Image

from app.extensions import db
from app.models import ProductiveSector, Role, SectorStatus, UnitSector, User, UserStatus


def _admin(client):
    user = User(
        username="admin.dominio",
        email="admin.dominio@gmail.com",
        role=Role.SUPERADMIN,
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
    return {
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
        "sectores": [{"productive_sector_id": str(sector_id)}],
    }


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


def test_solicitud_valida_formato_numerico_del_nit(app, client):
    with app.app_context():
        sector = ProductiveSector(nombre="Manufactura", es_otro=False)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    for invalid_nit in ("1234", "1234567890123", "123-456789", "ABC123456"):
        payload = _registration_payload(client, sector_id)
        payload["nit"] = invalid_nit
        response = client.post("/api/registration-requests", json=payload)
        assert response.status_code == 400

    for invalid_seprec in ("1234", "1234567890123", "123-456789", "SEPREC123"):
        payload = _registration_payload(client, sector_id)
        payload["registro_seprec"] = invalid_seprec
        response = client.post("/api/registration-requests", json=payload)
        assert response.status_code == 400

    for invalid_pro_bolivia in ("1234", "1234567890123", "123-456789", "PROBOL123"):
        payload = _registration_payload(client, sector_id)
        payload["registro_pro_bolivia"] = invalid_pro_bolivia
        response = client.post("/api/registration-requests", json=payload)
        assert response.status_code == 400

    valid_payload = _registration_payload(client, sector_id)
    valid_payload["nit"] = "12345"
    valid_payload["registro_seprec"] = "12345"
    valid_payload["registro_pro_bolivia"] = "12345"
    response = client.post("/api/registration-requests", json=valid_payload)
    assert response.status_code == 201


def test_solicitud_requiere_nombres_y_ambos_apellidos_del_representante(app, client):
    with app.app_context():
        sector = ProductiveSector(nombre="Madera", es_otro=False)
        db.session.add(sector)
        db.session.commit()
        sector_id = sector.id

    representative_fields = (
        "nombres_representante",
        "apellido_paterno_representante",
        "apellido_materno_representante",
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
        "app.controllers.registration_controller._temporary_password",
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


def test_catalogo_deriva_todos_los_productos_de_la_unidad(app, client, monkeypatch):
    monkeypatch.setattr(
        "app.controllers.registration_controller._temporary_password",
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
    authorized = client.post(
        f"/api/admin/fairs/{fair.json['id']}/participations/{participation.json['id']}/authorize",
        headers=admin_headers,
    )
    assert authorized.status_code == 200
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
        "capacidad_produccion_stock": "10 unidades",
    }
    for number in (4, 5):
        extra = client.post(
            "/api/productive-unit/products",
            headers=unit_headers,
            json={"nombre_comercial": f"Producto {number}", **base_product},
        )
        assert extra.status_code == 201
    sixth = client.post(
        "/api/productive-unit/products",
        headers=unit_headers,
        json={"nombre_comercial": "Producto 6", **base_product},
    )
    assert sixth.status_code == 409

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
