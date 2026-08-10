from datetime import datetime, timezone
import base64
from io import BytesIO
from pathlib import Path

import pytest
from flask import Flask
from flask_jwt_extended import create_access_token

from app import create_app
from app.configuracion import Config, validar_configuracion_segura
from app.servicios import (
    get_public_cache,
    invalidate_public_cache,
    set_public_cache,
)
from app.extensiones import db
from app.modelos import (
    Audit,
    CacheState,
    Category,
    DocumentType,
    Exhibitor,
    Product,
    ProductImage,
    ProductStatus,
    RegistrationRequest,
    RegistrationStatus,
    Role,
    User,
    UserStatus,
)


PASSWORD = "Temporal2026!"


def create_user(username, role=Role.ADMIN):
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
    db.session.commit()
    return user


def login(client, username):
    response = client.post(
        "/api/auth/login", json={"login": username, "password": PASSWORD}
    )
    assert response.status_code == 200
    return response.json["access_token"]


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_marshmallow_rechaza_campos_desconocidos(client):
    response = client.post(
        "/api/auth/login",
        json={"login": "nadie", "password": "x", "admin": True},
    )
    assert response.status_code == 400
    assert "admin" in response.json["details"]


def test_credenciales_temporales_no_se_exponen_si_estan_deshabilitadas(app, client):
    with app.app_context():
        create_user("actor")
        token = login(client, "actor")
    app.config["MOSTRAR_CREDENCIALES_TEMPORALES"] = False

    response = client.post(
        "/api/admin/users",
        headers=headers(token),
        json={
            "first_name": "Admin",
            "apellido_paterno": "Seguro",
            "email": "admin.seguro@gmail.com",
            "role": "ADMIN",
        },
    )

    assert response.status_code == 201
    assert "temporary_password" not in response.json


def test_produccion_rechaza_configuracion_incompleta(monkeypatch):
    for name in (
        "CLOUDINARY_URL",
        "CLAVE_BREVO",
        "CORREO_REMITENTE_BREVO",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENVIO_CORREO_HABILITADO", "true")
    production_app = Flask(__name__)
    production_app.config.update(
        TESTING=False,
        ENTORNO_APLICACION="produccion",
        SECRET_KEY=None,
        JWT_SECRET_KEY=None,
        SQLALCHEMY_DATABASE_URI="postgresql+psycopg://catalogo@db/catalogo",
        ORIGENES_PERMITIDOS=["http://localhost:5173"],
    )

    with pytest.raises(RuntimeError) as exc_info:
        validar_configuracion_segura(production_app)

    message = str(exc_info.value)
    assert "SECRET_KEY" in message
    assert "JWT_SECRET_KEY" in message
    assert "ORIGENES_PERMITIDOS" in message
    assert "CLOUDINARY_URL" in message
    assert "CLAVE_BREVO" in message


def test_paginacion_limita_y_reporta_totales(app, client):
    with app.app_context():
        create_user("actor")
        for index in range(24):
            create_user(f"admin{index:02d}", Role.ADMIN)
        token = login(client, "actor")

    response = client.get(
        "/api/admin/users?page=2&per_page=10", headers=headers(token)
    )
    assert response.status_code == 200
    assert len(response.json["items"]) == 10
    assert response.json["pagination"] == {
        "page": 2,
        "per_page": 10,
        "pages": 3,
        "total": 25,
        "has_next": True,
        "has_prev": True,
    }


def test_eliminacion_logica_admin_protege_actor(app, client):
    with app.app_context():
        actor = create_user("actor")
        target = create_user("target", Role.ADMIN)
        actor_id, target_id = actor.id, target.id
        token = login(client, "actor")
        target_token = login(client, "target")

    own = client.delete(f"/api/admin/users/{actor_id}", headers=headers(token))
    assert own.status_code == 409
    deleted = client.delete(f"/api/admin/users/{target_id}", headers=headers(token))
    assert deleted.status_code == 204
    unavailable = client.get("/api/auth/me", headers=headers(target_token))
    assert unavailable.status_code == 401

    with app.app_context():
        saved = db.session.get(User, target_id)
        assert saved.deleted_at is not None
        assert saved.status == UserStatus.INACTIVE


def test_cache_detecta_invalidacion_persistida(app):
    with app.app_context():
        invalidate_public_cache()
        set_public_cache(("catalog",), {"value": 1})
        assert get_public_cache(("catalog",)) == {"value": 1}
        state = db.session.get(CacheState, "catalogo_publico")
        state.version += 1
        db.session.commit()
        assert get_public_cache(("catalog",)) is None

        set_public_cache(("catalog",), {"value": 2})
        invalidate_public_cache()
        assert get_public_cache(("catalog",)) is None


def test_cache_no_entrega_datos_si_no_puede_validar_version(app, monkeypatch):
    with app.app_context():
        set_public_cache(("catalog",), {"value": 1})
        monkeypatch.setattr(
            "app.servicios.cache_publica.public_cache_version", lambda: None
        )
        assert get_public_cache(("catalog",)) is None

def test_upload_rechaza_archivo_que_no_es_imagen(app, client):
    with app.app_context():
        create_user("actor")
        token = login(client, "actor")

    response = client.post(
        "/api/uploads",
        headers=headers(token),
        data={"folder": "productos", "file": (BytesIO(b"no-image"), "fake.png")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_reset_test_db_rechaza_base_no_postgresql():
    class SQLiteTestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"

    sqlite_app = create_app(SQLiteTestConfig)
    runner = sqlite_app.test_cli_runner()
    result = runner.invoke(args=["reset-test-db", "--yes"])
    assert result.exit_code != 0
    assert "PostgreSQL" in result.output


def test_sync_fairs_elimina_tokens_revocados_expirados(app):
    from app.modelos import RevokedToken

    with app.app_context():
        db.session.add(
            RevokedToken(
                jti="00000000-0000-0000-0000-000000000001",
                expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
            )
        )
        db.session.commit()

    result = app.test_cli_runner().invoke(args=["sync-fairs"])
    assert result.exit_code == 0
    with app.app_context():
        assert db.session.query(RevokedToken).count() == 0


def test_cleanup_elimina_logo_de_solicitud_rechazada_vencida(app):
    with app.app_context():
        folder = Path(app.config["CARPETA_CARGAS"]) / "solicitudes"
        folder.mkdir(parents=True, exist_ok=True)
        logo = folder / "rechazada.png"
        logo.write_bytes(b"logo vencido")
        registration = RegistrationRequest(
            nombre_comercial="Rechazada",
            razon_social="Rechazada SRL",
            nombres_representante="Persona",
            apellido_paterno_representante="Prueba",
            apellido_materno_representante="Control",
            departamento="La Paz",
            direccion_fisica="Calle 1",
            telefono_whatsapp="71234567",
            correo_electronico="rechazada@example.com",
            resena_comercial="Solicitud rechazada",
            logo_url="/uploads/solicitudes/rechazada.png",
            estado=RegistrationStatus.REJECTED,
            updated_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        db.session.add(registration)
        db.session.commit()
        registration_id = registration.id

    result = app.test_cli_runner().invoke(args=["cleanup-registration-uploads"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert db.session.get(RegistrationRequest, registration_id).logo_url is None
        assert not logo.exists()
        assert db.session.scalar(
            db.select(Audit.id).where(
                Audit.accion == "LIMPIAR_ARCHIVOS_SOLICITUDES"
            )
        )


def test_expositor_no_puede_consultar_producto_ajeno(app, client):
    with app.app_context():
        first = create_user("expo1", Role.PRODUCTIVE_UNIT_RESPONSIBLE)
        second = create_user("expo2", Role.PRODUCTIVE_UNIT_RESPONSIBLE)
        first_exhibitor = Exhibitor(
            user_id=first.id,
            nombre_comercial="Primero",
            tipo_documento=DocumentType.CI,
            numero_documento="1001",
            nombre_responsable="Expo",
            apellido_responsable="Uno",
            telefono_whatsapp="59171234567",
            correo=first.email,
            departamento="La Paz",
            municipio="La Paz",
            estado=UserStatus.ACTIVE,
        )
        second_exhibitor = Exhibitor(
            user_id=second.id,
            nombre_comercial="Segundo",
            tipo_documento=DocumentType.CI,
            numero_documento="1002",
            nombre_responsable="Expo",
            apellido_responsable="Dos",
            telefono_whatsapp="59171234568",
            correo=second.email,
            departamento="La Paz",
            municipio="La Paz",
            estado=UserStatus.ACTIVE,
        )
        category = Category(nombre="Prueba", slug="prueba", estado=True)
        db.session.add_all([first_exhibitor, second_exhibitor, category])
        db.session.flush()
        product = Product(
            exhibitor_id=second_exhibitor.id,
            category_id=category.id,
            nombre="Producto ajeno",
            slug="producto-ajeno",
            descripcion="Prueba",
            estado=ProductStatus.AVAILABLE,
        )
        db.session.add(product)
        db.session.commit()
        product_id = product.id
        token = create_access_token(identity=str(first.id))

    response = client.get(
        f"/api/exhibitor/products/{product_id}", headers=headers(token)
    )
    assert response.status_code == 404


def test_imagen_producto_exige_datos_y_permite_varias(app, client):
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )
    with app.app_context():
        owner = create_user("expoimagenes", Role.PRODUCTIVE_UNIT_RESPONSIBLE)
        exhibitor = Exhibitor(
            user_id=owner.id,
            nombre_comercial="Taller de imágenes",
            tipo_documento=DocumentType.CI,
            numero_documento="9001",
            nombre_responsable="Expo",
            apellido_responsable="Imágenes",
            telefono_whatsapp="59171234569",
            correo=owner.email,
            departamento="La Paz",
            municipio="La Paz",
            estado=UserStatus.ACTIVE,
        )
        category = Category(nombre="Imágenes", slug="imagenes", estado=True)
        db.session.add_all([exhibitor, category])
        db.session.flush()
        product = Product(
            exhibitor_id=exhibitor.id,
            category_id=category.id,
            nombre="Producto con galería",
            slug="producto-con-galeria",
            descripcion="Prueba",
            estado=ProductStatus.AVAILABLE,
        )
        db.session.add(product)
        db.session.commit()
        product_id = product.id
        token = create_access_token(identity=str(owner.id))

    missing_alt = client.post(
        f"/api/exhibitor/products/{product_id}/images",
        headers=headers(token),
        data={"file": (BytesIO(png), "primera.png"), "display_order": "0"},
        content_type="multipart/form-data",
    )
    assert missing_alt.status_code == 400
    assert "texto alternativo" in missing_alt.json["error"].lower()

    image_ids = []
    for expected_order, submitted_order in enumerate((8, 3)):
        response = client.post(
            f"/api/exhibitor/products/{product_id}/images",
            headers=headers(token),
            data={
                "file": (BytesIO(png), f"imagen-{expected_order}.png"),
                "alt_text": f"Vista {expected_order + 1} del producto",
                "display_order": str(submitted_order),
                "is_cover": str(expected_order == 0).lower(),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code == 201
        assert response.json["display_order"] == expected_order
        image_ids.append(response.json["id"])

    with app.app_context():
        images = ProductImage.query.filter_by(product_id=product_id).all()
        assert len(images) == 2
        assert sorted(image.display_order for image in images) == [0, 1]

    third = client.post(
        f"/api/exhibitor/products/{product_id}/images",
        headers=headers(token),
        data={
            "file": (BytesIO(png), "imagen-3.png"),
            "alt_text": "Vista 3 del producto",
        },
        content_type="multipart/form-data",
    )
    assert third.status_code == 201
    fourth = client.post(
        f"/api/exhibitor/products/{product_id}/images",
        headers=headers(token),
        data={
            "file": (BytesIO(png), "imagen-4.png"),
            "alt_text": "Vista 4 del producto",
        },
        content_type="multipart/form-data",
    )
    assert fourth.status_code == 409
    assert client.delete(
        f"/api/product-images/{third.json['id']}", headers=headers(token)
    ).status_code == 204

    deleted = client.delete(
        f"/api/product-images/{image_ids[0]}", headers=headers(token)
    )
    assert deleted.status_code == 204
    with app.app_context():
        remaining = ProductImage.query.filter_by(product_id=product_id).one()
        assert remaining.display_order == 0
        assert remaining.is_cover is True
