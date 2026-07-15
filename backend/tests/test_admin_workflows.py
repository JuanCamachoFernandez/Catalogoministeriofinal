from datetime import date

from app.extensions import db
from app.models import (
    AssignmentStatus,
    Category,
    DocumentType,
    Exhibitor,
    Fair,
    FeriaStatus,
    Product,
    Role,
    User,
    UserStatus,
)


def admin_token(client):
    user = User(
        username="superadmin",
        email="superadmin@gmail.com",
        role=Role.SUPERADMIN,
        first_name="Super",
        last_name="Admin",
        status=UserStatus.ACTIVE,
        must_change_password=False,
    )
    user.set_password("Temporal2026!")
    db.session.add(user)
    db.session.commit()
    response = client.post(
        "/api/auth/login",
        json={"login": "superadmin", "password": "Temporal2026!"},
    )
    return user.id, response.json["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_publicar_feria_desactiva_la_anterior(app, client):
    with app.app_context():
        admin_id, token = admin_token(client)
        first = Fair(
            nombre="Feria Uno",
            slug="feria-uno",
            lugar="Plaza",
            departamento="La Paz",
            municipio="La Paz",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 1, 2),
            imagen_portada="/portada-1.jpg",
            estado=FeriaStatus.PUBLISHED,
            visible_publicamente=True,
            created_by=admin_id,
        )
        second = Fair(
            nombre="Feria Dos",
            slug="feria-dos",
            lugar="Campo",
            departamento="Cochabamba",
            municipio="Cochabamba",
            fecha_inicio=date(2026, 2, 1),
            fecha_fin=date(2026, 2, 2),
            imagen_portada="/portada-2.jpg",
            estado=FeriaStatus.DRAFT,
            visible_publicamente=False,
            created_by=admin_id,
        )
        db.session.add_all([first, second])
        db.session.commit()
        first_id, second_id = first.id, second.id

    response = client.patch(
        f"/api/fairs/{second_id}/status",
        headers=auth(token),
        json={"status": "PUBLISHED"},
    )
    assert response.status_code == 200

    with app.app_context():
        saved_first = db.session.get(Fair, first_id)
        saved_second = db.session.get(Fair, second_id)
        assert saved_first.estado == FeriaStatus.DISABLED
        assert saved_first.visible_publicamente is False
        assert saved_second.estado == FeriaStatus.PUBLISHED
        assert saved_second.visible_publicamente is True


def test_asignar_expositor_a_feria(app, client):
    with app.app_context():
        admin_id, token = admin_token(client)
        owner = User(
            username="expositor",
            email="expositor@gmail.com",
            role=Role.EXPOSITOR,
            first_name="Expo",
            last_name="Sitor",
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        owner.set_password("Temporal2026!")
        db.session.add(owner)
        db.session.flush()
        exhibitor = Exhibitor(
            user_id=owner.id,
            nombre_comercial="Artesanias",
            tipo_documento=DocumentType.CI,
            numero_documento="123",
            nombre_responsable="Expo",
            apellido_responsable="Sitor",
            telefono_whatsapp="59171234567",
            correo="expositor@gmail.com",
            departamento="La Paz",
            municipio="La Paz",
            estado=UserStatus.ACTIVE,
        )
        fair = Fair(
            nombre="Feria",
            slug="feria",
            lugar="Plaza",
            departamento="La Paz",
            municipio="La Paz",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 1, 2),
            imagen_portada="/portada.jpg",
            estado=FeriaStatus.DRAFT,
            visible_publicamente=False,
            created_by=admin_id,
        )
        db.session.add_all([exhibitor, fair])
        db.session.commit()
        fair_id, exhibitor_id = fair.id, exhibitor.id

    response = client.post(
        f"/api/fairs/{fair_id}/exhibitors",
        headers=auth(token),
        json={"exhibitor_id": str(exhibitor_id), "numero_stand": "A1"},
    )
    assert response.status_code == 201
    assert response.json["estado"] == AssignmentStatus.AUTHORIZED.value
    assert response.json["numero_stand"] == "A1"


def test_admin_crea_producto_con_precio(app, client):
    with app.app_context():
        _, token = admin_token(client)
        owner = User(
            username="expositor",
            email="expositor@gmail.com",
            role=Role.EXPOSITOR,
            first_name="Expo",
            last_name="Sitor",
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        owner.set_password("Temporal2026!")
        db.session.add(owner)
        db.session.flush()
        exhibitor = Exhibitor(
            user_id=owner.id,
            nombre_comercial="Artesanias",
            tipo_documento=DocumentType.CI,
            numero_documento="123",
            nombre_responsable="Expo",
            apellido_responsable="Sitor",
            telefono_whatsapp="59171234567",
            correo="expositor@gmail.com",
            departamento="La Paz",
            municipio="La Paz",
            estado=UserStatus.ACTIVE,
        )
        category = Category(nombre="Artesania", slug="artesania", estado=True)
        db.session.add_all([exhibitor, category])
        db.session.commit()
        exhibitor_id, category_id = exhibitor.id, category.id

    response = client.post(
        "/api/products",
        headers=auth(token),
        json={
            "exhibitor_id": str(exhibitor_id),
            "category_id": str(category_id),
            "nombre": "Producto",
            "descripcion": "Descripcion",
            "precio": "25.50",
        },
    )
    assert response.status_code == 201
    assert response.json["precio"] == 25.5

    with app.app_context():
        assert db.session.query(Product).count() == 1
