from datetime import timedelta
from pathlib import Path

from app.controllers.fair_controller import sync_fair_lifecycle
from app.extensions import db
from app.models import (
    AssignmentStatus,
    Category,
    DocumentType,
    Exhibitor,
    Fair,
    FairExhibitor,
    FairImage,
    FeriaStatus,
    Product,
    ProductStatus,
    Role,
    User,
    UserStatus,
    bolivia_today,
)


def create_catalog(today):
    admin = User(
        username="admin",
        email="admin@gmail.com",
        password_hash="hash",
        role=Role.SUPERADMIN,
        first_name="Admin",
        last_name="Test",
        status=UserStatus.ACTIVE,
        must_change_password=False,
    )
    owner = User(
        username="owner",
        email="owner@gmail.com",
        password_hash="hash",
        role=Role.EXPOSITOR,
        first_name="Owner",
        last_name="Test",
        status=UserStatus.ACTIVE,
        must_change_password=False,
    )
    admin.set_password("Temporal2026!")
    owner.set_password("Temporal2026!")
    db.session.add_all([admin, owner])
    db.session.flush()
    exhibitor = Exhibitor(
        user_id=owner.id,
        nombre_comercial="Empresa",
        tipo_documento=DocumentType.CI,
        numero_documento="100",
        nombre_responsable="Owner",
        apellido_responsable="Test",
        telefono_whatsapp="59171234567",
        correo="owner@gmail.com",
        departamento="La Paz",
        municipio="La Paz",
        estado=UserStatus.ACTIVE,
    )
    category = Category(nombre="Textiles", slug="textiles", estado=True)
    fair = Fair(
        nombre="Feria activa",
        slug="feria-activa",
        lugar="Plaza",
        departamento="La Paz",
        municipio="La Paz",
        fecha_inicio=today,
        fecha_fin=today + timedelta(days=1),
        estado=FeriaStatus.PUBLISHED,
        visible_publicamente=True,
        created_by=admin.id,
    )
    db.session.add_all([exhibitor, category, fair])
    db.session.flush()
    assignment = FairExhibitor(
        fair_id=fair.id,
        exhibitor_id=exhibitor.id,
        estado=AssignmentStatus.AUTHORIZED,
    )
    first = Product(
        exhibitor_id=exhibitor.id,
        category_id=category.id,
        nombre="Producto uno",
        slug="producto-uno",
        descripcion="Descripción",
        estado=ProductStatus.AVAILABLE,
    )
    db.session.add_all([assignment, first])
    db.session.commit()
    return admin, exhibitor, category, fair, assignment, first


def test_finalizar_elimina_imagenes_y_conserva_registro(app):
    with app.app_context():
        today = bolivia_today()
        admin, _, _, _, _, _ = create_catalog(today)
        upload_folder = Path(app.config["UPLOAD_FOLDER"]) / "ferias"
        upload_folder.mkdir(parents=True)
        cover = upload_folder / "cover.png"
        gallery = upload_folder / "gallery.png"
        cover.write_bytes(b"cover")
        gallery.write_bytes(b"gallery")
        fair = Fair(
            nombre="Feria pasada",
            slug="feria-pasada",
            lugar="Plaza",
            departamento="La Paz",
            municipio="La Paz",
            fecha_inicio=today - timedelta(days=3),
            fecha_fin=today - timedelta(days=2),
            imagen_portada="/uploads/ferias/cover.png",
            estado=FeriaStatus.DRAFT,
            visible_publicamente=False,
            created_by=admin.id,
        )
        db.session.add(fair)
        db.session.flush()
        db.session.add(
            FairImage(
                fair_id=fair.id,
                filename="gallery.png",
                url="/uploads/ferias/gallery.png",
            )
        )
        db.session.commit()
        fair_id = fair.id

        assert sync_fair_lifecycle(today) is True
        saved = db.session.get(Fair, fair_id)
        assert saved.estado == FeriaStatus.FINISHED
        assert saved.imagen_portada is None
        assert db.session.query(FairImage).filter_by(fair_id=fair_id).count() == 0
        assert not cover.exists()
        assert not gallery.exists()


def test_detecta_solapamiento(app):
    with app.app_context():
        today = bolivia_today()
        create_catalog(today)
        assert Fair.has_overlap(today + timedelta(days=1), today + timedelta(days=2))
        assert not Fair.has_overlap(today + timedelta(days=3), today + timedelta(days=4))


def test_productos_se_derivan_y_revocacion_los_retira(app, client):
    with app.app_context():
        today = bolivia_today()
        _, exhibitor, category, _, assignment, _ = create_catalog(today)
        exhibitor_id = exhibitor.id
        assignment_id = assignment.id
        db.session.add(
            Product(
                exhibitor_id=exhibitor.id,
                category_id=category.id,
                nombre="Producto dos",
                slug="producto-dos",
                descripcion="Descripción",
                estado=ProductStatus.OUT_OF_STOCK,
            )
        )
        db.session.commit()

    response = client.get(
        f"/api/public/fairs/feria-activa/exhibitors/{exhibitor_id}"
    )
    assert response.status_code == 200
    assert len(response.json["productos"]) == 2

    login = client.post(
        "/api/auth/login",
        json={"login": "admin", "password": "Temporal2026!"},
    )
    token = login.json["access_token"]
    revoked = client.patch(
        f"/api/fair-exhibitors/{assignment_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"estado": "REVOKED"},
    )
    assert revoked.status_code == 200
    hidden = client.get(
        f"/api/public/fairs/feria-activa/exhibitors/{exhibitor_id}"
    )
    assert hidden.status_code == 404


def test_feria_terminal_bloquea_cambios_de_asignacion(app, client):
    with app.app_context():
        today = bolivia_today()
        _, _, _, fair, assignment, _ = create_catalog(today)
        fair_id, assignment_id = fair.id, assignment.id

    login = client.post(
        "/api/auth/login",
        json={"login": "admin", "password": "Temporal2026!"},
    )
    headers = {"Authorization": f"Bearer {login.json['access_token']}"}
    closed = client.patch(
        f"/api/fairs/{fair_id}/status",
        headers=headers,
        json={"status": "FINISHED"},
    )
    assert closed.status_code == 200
    update = client.patch(
        f"/api/fair-exhibitors/{assignment_id}",
        headers=headers,
        json={"numero_stand": "B2"},
    )
    assert update.status_code == 409
