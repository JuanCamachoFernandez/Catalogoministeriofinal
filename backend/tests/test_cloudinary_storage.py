from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.extensiones import db
from app.modelos import (
    Fair,
    ExhibitorType,
    Product,
    ProductImage,
    ProductiveSector,
    ProductiveUnit,
    ProductiveUnitStatus,
    RegistrationRequest,
    RegistrationStatus,
    Role,
    User,
    UserStatus,
    bolivia_today,
)


def _png_bytes(color="green"):
    stream = BytesIO()
    Image.new("RGB", (8, 8), color).save(stream, format="PNG")
    stream.seek(0)
    return stream


def _invalid_file():
    return BytesIO(b"not-an-image")


def _admin_headers(client):
    user = User(
        username="admin.cloudinary",
        email="admin.cloudinary@gmail.com",
        role=Role.SUPERADMIN,
        first_name="Admin",
        last_name="Cloudinary",
        status=UserStatus.ACTIVE,
        must_change_password=False,
    )
    user.set_password("AdminCloudinary2026!")
    db.session.add(user)
    db.session.commit()
    response = client.post(
        "/api/auth/login",
        json={"login": user.username, "password": "AdminCloudinary2026!"},
    )
    return {"Authorization": f"Bearer {response.json['access_token']}"}


@pytest.fixture
def cloudinary_mocks(monkeypatch):
    uploads = []
    destroys = []

    def fake_upload(stream, **kwargs):
        index = len(uploads) + 1
        folder = kwargs["folder"]
        public_id = f"{folder}/{kwargs['public_id']}"
        uploads.append({"folder": folder, "public_id": public_id})
        return {
            "secure_url": f"https://res.cloudinary.com/demo/image/upload/v1/{public_id}.png",
            "public_id": public_id,
        }

    def fake_destroy(public_id, **kwargs):
        destroys.append({"public_id": public_id, "kwargs": kwargs})
        return {"result": "ok"}

    class FakeUploader:
        @staticmethod
        def upload(stream, **kwargs):
            return fake_upload(stream, **kwargs)

        @staticmethod
        def destroy(public_id, **kwargs):
            return fake_destroy(public_id, **kwargs)

    monkeypatch.setattr("app.servicios.archivos._cloudinary_uploader", lambda: FakeUploader)
    return {"uploads": uploads, "destroys": destroys}


def _create_sector():
    sector = ProductiveSector(nombre="Textiles", es_otro=False)
    db.session.add(sector)
    db.session.commit()
    return sector.id


def _upload_request_logo(client):
    response = client.post(
        "/api/registration-requests/logo",
        data={"file": (_png_bytes(), "logo.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    return response.json["logo_url"]


def _upload_request_product_image(client, filename):
    response = client.post(
        "/api/registration-requests/products/image",
        data={"file": (_png_bytes(), filename)},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    return response.json["imagen_url"]


def _registration_payload(client, sector_id, email="ana@manos.bo", nit="123456789"):
    return {
        "nombre_comercial": "Manos Andinas",
        "razon_social": "Manos Andinas SRL",
        "nit": nit,
        "nombres_representante": "Ana Maria",
        "apellido_paterno_representante": "Quispe",
        "apellido_materno_representante": "Mamani",
        "departamento": "La Paz",
        "direccion_fisica": "Calle 1",
        "telefono_whatsapp": "76543210",
        "correo_electronico": email,
        "resena_comercial": "Artesania boliviana",
        "logo_url": _upload_request_logo(client),
        "sectores": [{"productive_sector_id": str(sector_id)}],
        "productos": [
            {
                "nombre_comercial": f"Producto {index + 1}",
                "descripcion_tecnica": "Descripcion tecnica",
                "precio_referencia": "10.00",
                "imagen_url": _upload_request_product_image(client, f"producto-{index + 1}.png"),
            }
            for index in range(3)
        ],
    }


def _approve_unit(app, client, monkeypatch):
    monkeypatch.setattr(
        "app.rutas.solicitudes_registro._temporary_password",
        lambda: "TemporalUnidad2026!",
    )
    with app.app_context():
        sector_id = _create_sector()
        admin_headers = _admin_headers(client)
    created = client.post(
        "/api/registration-requests",
        json=_registration_payload(client, sector_id),
    )
    assert created.status_code == 201
    approved = client.post(
        f"/api/admin/registration-requests/{created.json['id']}/approve",
        headers=admin_headers,
        json={},
    )
    assert approved.status_code == 200
    login = client.post(
        "/api/auth/login",
        json={"login": "ana@manos.bo", "password": "TemporalUnidad2026!"},
    )
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
    profile = client.get("/api/productive-unit/profile", headers=unit_headers)
    return admin_headers, unit_headers, UUID(profile.json["id"])


def test_registration_logo_and_unit_logo_store_cloudinary_urls(app, client, cloudinary_mocks, monkeypatch):
    admin_headers, unit_headers, unit_id = _approve_unit(app, client, monkeypatch)

    with app.app_context():
        request_item = db.session.scalar(
            select(RegistrationRequest).where(
                RegistrationRequest.correo_electronico == "ana@manos.bo"
            )
        )
        unit = db.session.get(ProductiveUnit, unit_id)
        assert request_item.logo_url.startswith("https://res.cloudinary.com/")
        assert request_item.logo_public_id.startswith("catalogo-ministerio/solicitudes/")
        assert unit.logo_url == request_item.logo_url
        assert unit.logo_public_id == request_item.logo_public_id

    uploaded_logo = client.post(
        "/api/productive-unit/logo",
        headers=unit_headers,
        data={"file": (_png_bytes("blue"), "nuevo-logo.png")},
        content_type="multipart/form-data",
    )
    assert uploaded_logo.status_code == 201

    with app.app_context():
        unit = db.session.get(ProductiveUnit, unit_id)
        assert unit.logo_url.startswith("https://res.cloudinary.com/")
        assert unit.logo_public_id.startswith("catalogo-ministerio/unidades_productivas/")


def test_generic_upload_and_admin_profile_photo_use_cloudinary(app, client, cloudinary_mocks):
    with app.app_context():
        admin_headers = _admin_headers(client)

    uploaded = client.post(
        "/api/uploads",
        headers=admin_headers,
        data={"folder": "perfiles", "file": (_png_bytes("cyan"), "perfil.png")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 201
    assert uploaded.json["url"].startswith("https://res.cloudinary.com/")

    updated = client.patch(
        "/api/admin/profile",
        headers=admin_headers,
        json={"foto_perfil": uploaded.json["url"]},
    )
    assert updated.status_code == 200

    with app.app_context():
        user = db.session.scalar(select(User).where(User.username == "admin.cloudinary"))
        assert user.foto_perfil == uploaded.json["url"]
        assert user.foto_perfil_public_id.startswith("catalogo-ministerio/perfiles/")


def test_product_image_upload_replace_and_delete_use_cloudinary(app, client, cloudinary_mocks, monkeypatch):
    _, unit_headers, _ = _approve_unit(app, client, monkeypatch)

    products = client.get("/api/productive-unit/products", headers=unit_headers)
    product_id = products.json["items"][0]["id"]
    initial_image_id = products.json["items"][0]["imagenes"][0]["id"]

    added = client.post(
        f"/api/productive-unit/products/{product_id}/images",
        headers=unit_headers,
        data={"file": (_png_bytes("red"), "detalle.png"), "alt_text": "Detalle"},
        content_type="multipart/form-data",
    )
    assert added.status_code == 201

    replaced = client.patch(
        f"/api/productive-unit/products/{product_id}/images/{initial_image_id}",
        headers=unit_headers,
        data={"file": (_png_bytes("yellow"), "reemplazo.png"), "alt_text": "Principal"},
        content_type="multipart/form-data",
    )
    assert replaced.status_code == 200

    delete_target = next(
        image["id"]
        for image in replaced.json["imagenes"]
        if image["texto_alternativo"] == "Detalle"
    )
    deleted = client.delete(
        f"/api/productive-unit/products/{product_id}/images/{delete_target}",
        headers=unit_headers,
    )
    assert deleted.status_code == 204
    assert len(cloudinary_mocks["destroys"]) >= 2

    with app.app_context():
        image = db.session.get(ProductImage, UUID(initial_image_id))
        assert image.public_id.startswith("catalogo-ministerio/productos/")


def test_fair_cover_and_gallery_use_cloudinary(app, client, cloudinary_mocks):
    with app.app_context():
        admin_headers = _admin_headers(client)
    today = bolivia_today().isoformat()
    created = client.post(
        "/api/admin/fairs",
        headers=admin_headers,
        json={
            "nombre": "Feria Cloudinary",
            "ubicacion": "La Paz",
            "fecha_inicio": today,
            "fecha_fin": today,
        },
    )
    assert created.status_code == 201
    fair_id = created.json["id"]

    cover = client.post(
        f"/api/admin/fairs/{fair_id}/cover",
        headers=admin_headers,
        data={"file": (_png_bytes("purple"), "cover.png")},
        content_type="multipart/form-data",
    )
    assert cover.status_code == 201

    gallery = client.post(
        f"/api/fairs/{fair_id}/images",
        headers=admin_headers,
        data={"file": (_png_bytes("orange"), "gallery.png"), "alt_text": "Galeria"},
        content_type="multipart/form-data",
    )
    assert gallery.status_code == 201

    with app.app_context():
        fair = db.session.get(Fair, UUID(fair_id))
        assert fair.imagen_portada_public_id.startswith("catalogo-ministerio/ferias/")


def test_exhibitor_rejects_external_logo_urls(app, client):
    with app.app_context():
        admin_headers = _admin_headers(client)
        exhibitor_type = ExhibitorType(nombre="Productor")
        db.session.add(exhibitor_type)
        db.session.commit()
        type_id = exhibitor_type.id

    response = client.post(
        "/api/exhibitors",
        headers=admin_headers,
        json={
            "nombre_comercial": "Productos Andinos",
            "tipo_documento": "CI",
            "numero_documento": "4455667",
            "nombre_responsable": "Maria",
            "apellido_paterno_responsable": "Lopez",
            "apellido_materno_responsable": "Quispe",
            "correo": "maria.logo@gmail.com",
            "telefono_whatsapp": "71234567",
            "departamento": "La Paz",
            "municipio": "La Paz",
            "logo": "https://imagenes.example/logo.png",
            "type_ids": [str(type_id)],
        },
    )
    assert response.status_code == 400


def test_legacy_request_logo_cleanup_without_public_id(app, client):
    with app.app_context():
        sector_id = _create_sector()
        folder = Path(app.config["CARPETA_CARGAS"]) / "solicitudes"
        folder.mkdir(parents=True, exist_ok=True)
        legacy_path = folder / "legacy-logo.png"
        legacy_path.write_bytes(_png_bytes().getvalue())
        item = RegistrationRequest(
            nombre_comercial="Legacy",
            razon_social="Legacy SRL",
            nit="987654321",
            nombres_representante="Lidia",
            apellido_paterno_representante="Perez",
            apellido_materno_representante="Lopez",
            departamento="La Paz",
            direccion_fisica="Calle 2",
            telefono_whatsapp="76543210",
            correo_electronico="legacy@manos.bo",
            resena_comercial="Legacy",
            logo_url="/uploads/solicitudes/legacy-logo.png",
            logo_public_id=None,
            estado=RegistrationStatus.PENDING,
        )
        db.session.add(item)
        db.session.commit()
        item_id = item.id
        admin_headers = _admin_headers(client)

    rejected = client.post(
        f"/api/admin/registration-requests/{item_id}/reject",
        headers=admin_headers,
        json={"motivo": "Observaciones"},
    )
    assert rejected.status_code == 200
    assert not legacy_path.exists()

    with app.app_context():
        item = db.session.get(RegistrationRequest, item_id)
        assert item.logo_url is None
        assert item.logo_public_id is None


def test_rejects_invalid_image_file_on_registration_logo(client, cloudinary_mocks):
    response = client.post(
        "/api/registration-requests/logo",
        data={"file": (_invalid_file(), "logo.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_cloudinary_failure_returns_controlled_error(client, monkeypatch):
    class FailingUploader:
        @staticmethod
        def upload(*args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "app.servicios.archivos._cloudinary_uploader",
        lambda: FailingUploader,
    )
    response = client.post(
        "/api/registration-requests/logo",
        data={"file": (_png_bytes(), "logo.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert response.json["error"] == "No fue posible subir la imagen"


def test_product_image_db_failure_cleans_up_uploaded_cloudinary_resource(app, client, cloudinary_mocks, monkeypatch):
    _, unit_headers, _ = _approve_unit(app, client, monkeypatch)
    product_id = client.get("/api/productive-unit/products", headers=unit_headers).json["items"][0]["id"]

    original_commit = db.session.commit
    state = {"failed": False}

    def failing_commit():
        if not state["failed"]:
            state["failed"] = True
            raise SQLAlchemyError("db fail")
        return original_commit()

    monkeypatch.setattr(db.session, "commit", failing_commit)
    response = client.post(
        f"/api/productive-unit/products/{product_id}/images",
        headers=unit_headers,
        data={"file": (_png_bytes("black"), "falla.png"), "alt_text": "Falla"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 409
    assert cloudinary_mocks["destroys"][-1]["public_id"].startswith(
        "catalogo-ministerio/productos/"
    )
