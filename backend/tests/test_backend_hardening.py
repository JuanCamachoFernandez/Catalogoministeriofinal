from datetime import datetime, timezone
from io import BytesIO

from flask_jwt_extended import create_access_token

from app.controllers.common import (
    get_public_cache,
    invalidate_public_cache,
    set_public_cache,
)
from app.extensions import db
from app.models import (
    CacheState,
    Category,
    DocumentType,
    Exhibitor,
    Product,
    ProductStatus,
    Role,
    User,
    UserStatus,
)


PASSWORD = "Temporal2026!"


def create_user(username, role=Role.SUPERADMIN):
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


def test_paginacion_limita_y_reporta_totales(app, client):
    with app.app_context():
        create_user("actor")
        for index in range(24):
            create_user(f"admin{index:02d}", Role.ADMIN_VICEMINISTERIO)
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
        target = create_user("target", Role.ADMIN_VICEMINISTERIO)
        actor_id, target_id = actor.id, target.id
        token = login(client, "actor")
        target_token = login(client, "target")

    own = client.delete(f"/api/admin/users/{actor_id}", headers=headers(token))
    assert own.status_code == 409
    deleted = client.delete(f"/api/admin/users/{target_id}", headers=headers(token))
    assert deleted.status_code == 204
    unavailable = client.get("/api/auth/me", headers=headers(target_token))
    assert unavailable.status_code == 403

    with app.app_context():
        saved = db.session.get(User, target_id)
        assert saved.deleted_at is not None
        assert saved.status == UserStatus.INACTIVE


def test_cache_detecta_invalidacion_persistida(app):
    with app.app_context():
        invalidate_public_cache()
        set_public_cache(("catalog",), {"value": 1})
        assert get_public_cache(("catalog",)) == {"value": 1}
        state = db.session.get(CacheState, "public_catalog")
        state.version += 1
        db.session.commit()
        assert get_public_cache(("catalog",)) is None

        set_public_cache(("catalog",), {"value": 2})
        invalidate_public_cache()
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


def test_reset_test_db_rechaza_base_no_postgresql(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["reset-test-db", "--yes"])
    assert result.exit_code != 0
    assert "PostgreSQL" in result.output


def test_sync_fairs_elimina_tokens_revocados_expirados(app):
    from app.models import RevokedToken

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


def test_expositor_no_puede_consultar_producto_ajeno(app, client):
    with app.app_context():
        first = create_user("expo1", Role.EXPOSITOR)
        second = create_user("expo2", Role.EXPOSITOR)
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
