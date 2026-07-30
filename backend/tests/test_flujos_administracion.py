from datetime import timedelta
from io import BytesIO

from PIL import Image
from openpyxl import load_workbook

from app.extensiones import db
from app.modelos import (
    AdminProfile,
    AssignmentStatus,
    AdminUnit,
    Category,
    DocumentType,
    Exhibitor,
    ExhibitorType,
    Fair,
    FeriaStatus,
    Product,
    Role,
    User,
    UserStatus,
    bolivia_today,
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


def _png_file(name="imagen.png", color="green"):
    stream = BytesIO()
    Image.new("RGB", (8, 8), color).save(stream, format="PNG")
    stream.seek(0)
    return stream, name


def test_administrador_edita_su_propio_perfil(app, client):
    with app.app_context():
        user_id, token = admin_token(client)
        user = db.session.get(User, user_id)
        user.role = Role.ADMIN_VICEMINISTERIO
        db.session.commit()

    response = client.patch(
        "/api/admin/profile",
        headers=auth(token),
        json={
            "first_name": "Daniel",
            "apellido_paterno": "Camacho",
            "apellido_materno": "Fernandez",
            "numero_documento": "778899",
            "email": "danielperfil@gmail.com",
            "phone": "71234567",
            "cargo": "Técnico",
            "unidad": "Catálogo",
        },
    )
    assert response.status_code == 200
    assert response.json["first_name"] == "Daniel"
    assert response.json["apellido_paterno"] == "Camacho"
    assert response.json["numero_documento"] == "778899"

    own_profile = client.get("/api/admin/profile", headers=auth(token))
    assert own_profile.status_code == 200
    assert own_profile.json["unidad"] == "Catálogo"
    with app.app_context():
        profile = db.session.scalar(
            db.select(AdminProfile).where(AdminProfile.user_id == user_id)
        )
        assert profile.cargo == "Técnico"


def test_administrador_puede_restaurar_expositor_pero_no_otro_admin(app, client):
    with app.app_context():
        actor = User(
            username="adminunidad",
            email="adminunidad@gmail.com",
            role=Role.ADMIN_VICEMINISTERIO,
            first_name="Admin",
            last_name="Unidad",
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        actor.set_password("Temporal2026!")
        exhibitor_user = User(
            username="expositorprueba",
            email="expositorprueba@gmail.com",
            role=Role.EXPOSITOR,
            first_name="Rosa",
            last_name="Quispe",
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        exhibitor_user.set_password("Anterior2026!")
        db.session.add_all([actor, exhibitor_user])
        db.session.flush()
        db.session.add(
            Exhibitor(
                user_id=exhibitor_user.id,
                nombre_comercial="Artesanías Rosa",
                tipo_documento=DocumentType.CI,
                numero_documento="7654321",
                nombre_responsable="Rosa",
                apellido_responsable="Quispe",
                apellido_paterno_responsable="Quispe",
                telefono_whatsapp="59171234567",
                correo="expositorprueba@gmail.com",
                departamento="La Paz",
                municipio="La Paz",
                estado=UserStatus.ACTIVE,
            )
        )
        db.session.commit()
        actor_id, exhibitor_user_id = actor.id, exhibitor_user.id

    login = client.post(
        "/api/auth/login",
        json={"login": "adminunidad", "password": "Temporal2026!"},
    )
    token = login.json["access_token"]
    restored = client.post(
        f"/api/admin/users/{exhibitor_user_id}/reset-password",
        headers=auth(token),
    )
    assert restored.status_code == 200
    assert restored.json["temporary_password"] == "7654321RQ"

    forbidden = client.post(
        f"/api/admin/users/{actor_id}/reset-password",
        headers=auth(token),
    )
    assert forbidden.status_code == 403


def test_reportes_pdf_excel_y_opciones(app, client):
    with app.app_context():
        _, token = admin_token(client)
        db.session.add(
            Category(
                nombre="Textiles",
                slug="textiles",
                descripcion="Productos textiles",
                estado=True,
            )
        )
        db.session.commit()

    options = client.get("/api/reports/options", headers=auth(token))
    assert options.status_code == 200
    assert any(item["value"] == "categorias" for item in options.json["resources"])

    excel = client.get(
        "/api/reports/categorias?format=xlsx&status=active&columns=nombre,estado",
        headers=auth(token),
    )
    assert excel.status_code == 200
    assert excel.data.startswith(b"PK")
    assert "reporte_categorias_" in excel.headers["Content-Disposition"]
    workbook = load_workbook(BytesIO(excel.data), read_only=True)
    sheet = workbook["Categorías"]
    assert list(sheet.values)[0] == ("Categoría", "Estado")
    assert list(sheet.values)[1][0] == "Textiles"

    pdf = client.get(
        "/api/reports/general?format=pdf",
        headers=auth(token),
    )
    assert pdf.status_code == 200
    assert pdf.data.startswith(b"%PDF")
    assert pdf.mimetype == "application/pdf"

    invalid = client.get(
        "/api/reports/ferias?format=pdf&date_from=no-es-fecha",
        headers=auth(token),
    )
    assert invalid.status_code == 400


def test_admin_guarda_apellidos_separados(app, client):
    with app.app_context():
        _, token = admin_token(client)

    response = client.post(
        "/api/admin/users",
        headers=auth(token),
        json={
            "first_name": "Juana",
            "apellido_paterno": "Quispe",
            "apellido_materno": "Mamani",
            "numero_documento": "12345678",
            "email": "juana.quispe@gmail.com",
            "phone": "71234567",
            "unidad": "Promoción Productiva",
            "role": "ADMIN_VICEMINISTERIO",
        },
    )

    assert response.status_code == 201
    assert response.json["data"]["apellido_paterno"] == "Quispe"
    assert response.json["data"]["apellido_materno"] == "Mamani"
    assert response.json["data"]["numero_documento"] == "12345678"
    assert response.json["username"] == response.json["data"]["username"]
    assert response.json["temporary_password"] == "12345678JQ"
    with app.app_context():
        saved = db.session.scalar(
            db.select(User).where(User.email == "juana.quispe@gmail.com")
        )
        assert saved.apellido_paterno == "Quispe"
        assert saved.apellido_materno == "Mamani"
        assert saved.admin_profile.numero_documento == "12345678"
        assert saved.admin_profile.unidad == "Promoción Productiva"
        assert db.session.scalar(
            db.select(AdminUnit).where(AdminUnit.nombre == "Promoción Productiva")
        )
        assert saved.check_password("12345678JQ")

    units = client.get("/api/admin/units", headers=auth(token))
    assert units.status_code == 200
    assert "Promoción Productiva" in [item["nombre"] for item in units.json["items"]]


def test_admin_acepta_last_name_de_clientes_antiguos(app, client):
    with app.app_context():
        _, token = admin_token(client)

    response = client.post(
        "/api/admin/users",
        headers=auth(token),
        json={
            "first_name": "Cliente",
            "last_name": "Anterior",
            "numero_documento": "87654321",
            "email": "cliente.anterior@gmail.com",
            "role": "ADMIN_VICEMINISTERIO",
        },
    )

    assert response.status_code == 201
    assert response.json["data"]["apellido_paterno"] == "Anterior"
    assert response.json["data"]["apellido_materno"] is None
    assert response.json["temporary_password"] == "87654321CA"


def test_editar_admin_ignora_role_enviado_por_formulario_anterior(app, client):
    with app.app_context():
        admin_id, token = admin_token(client)

    response = client.patch(
        f"/api/admin/users/{admin_id}",
        headers=auth(token),
        json={
            "first_name": "Super",
            "apellido_paterno": "Admin",
            "email": "superadmin@gmail.com",
            "role": "SUPERADMIN",
        },
    )

    assert response.status_code == 200
    assert response.json["role"] == "SUPERADMIN"


def test_superadmin_cambia_rol_y_revoca_la_sesion_del_usuario(app, client):
    with app.app_context():
        _, token = admin_token(client)
        target = User(
            username="administrador.objetivo",
            email="administrador.objetivo@gmail.com",
            role=Role.ADMIN_VICEMINISTERIO,
            first_name="Administrador",
            last_name="Objetivo",
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        target.set_password("TemporalObjetivo2026!")
        db.session.add(target)
        db.session.commit()
        target_id = target.id
    target_login = client.post(
        "/api/auth/login",
        json={
            "login": "administrador.objetivo",
            "password": "TemporalObjetivo2026!",
        },
    )
    response = client.patch(
        f"/api/admin/users/{target_id}",
        headers=auth(token),
        json={"role": "ADMIN"},
    )
    assert response.status_code == 200
    assert response.json["role"] == "ADMIN"
    assert client.get(
        "/api/auth/me",
        headers=auth(target_login.json["access_token"]),
    ).status_code == 401


def test_expositor_usa_documento_e_iniciales_como_contrasena(app, client):
    with app.app_context():
        _, token = admin_token(client)
        exhibitor_type = ExhibitorType(nombre="Productor")
        db.session.add(exhibitor_type)
        db.session.commit()
        type_id = exhibitor_type.id
    upload = client.post(
        "/api/uploads",
        headers=auth(token),
        data={"folder": "logos", "file": _png_file("logo.png")},
        content_type="multipart/form-data",
    )
    assert upload.status_code == 201

    response = client.post(
        "/api/exhibitors",
        headers=auth(token),
        json={
            "nombre_comercial": "Productos Andinos",
            "tipo_documento": "CI",
            "numero_documento": "4455667",
            "nombre_responsable": "María",
            "apellido_paterno_responsable": "López",
            "apellido_materno_responsable": "Quispe",
            "correo": "maria.lopez@gmail.com",
            "telefono_whatsapp": "71234567",
            "departamento": "La Paz",
            "municipio": "La Paz",
            "logo": upload.json["url"],
            "type_ids": [str(type_id)],
        },
    )

    assert response.status_code == 201
    assert response.json["temporary_password"] == "4455667ML"
    assert response.json["data"]["apellido_paterno_responsable"] == "López"
    assert response.json["data"]["apellido_materno_responsable"] == "Quispe"
    assert response.json["data"]["logo"] == upload.json["url"]
    unchanged_exhibitor = response.json["data"]
    unchanged_update = client.patch(
        f"/api/exhibitors/{response.json['data']['id']}",
        headers=auth(token),
        json=unchanged_exhibitor,
    )
    assert unchanged_update.status_code == 200
    reset = client.post(
        f"/api/admin/users/{response.json['data']['user_id']}/reset-password",
        headers=auth(token),
    )
    assert reset.status_code == 200
    assert reset.json["temporary_password"] == "4455667ML"
    search = client.get("/api/exhibitors?q=Quispe", headers=auth(token))
    assert search.status_code == 200
    assert search.json["pagination"]["total"] == 1
    with app.app_context():
        saved = db.session.scalar(
            db.select(User).where(User.email == "maria.lopez@gmail.com")
        )
        assert saved.check_password("4455667ML")
        assert saved.exhibitor.apellido_paterno_responsable == "López"
        assert saved.exhibitor.apellido_materno_responsable == "Quispe"


def test_expositor_exige_un_tipo_y_nombre_de_organizacion(app, client):
    with app.app_context():
        _, token = admin_token(client)
        association = ExhibitorType(nombre="Asociación")
        producer = ExhibitorType(nombre="Productor")
        db.session.add_all([association, producer])
        db.session.commit()
        association_id, producer_id = association.id, producer.id

    payload = {
        "nombre_comercial": "Mujeres Productoras",
        "tipo_documento": "NIT",
        "numero_documento": "99887766",
        "nombre_responsable": "Ana",
        "apellido_paterno_responsable": "Mamani",
        "apellido_materno_responsable": "Quispe",
        "correo": "ana.mamani@gmail.com",
        "telefono_whatsapp": "71234567",
        "departamento": "La Paz",
        "municipio": "La Paz",
        "type_ids": [str(association_id)],
    }
    missing_name = client.post("/api/exhibitors", headers=auth(token), json=payload)
    assert missing_name.status_code == 400

    multiple = client.post(
        "/api/exhibitors",
        headers=auth(token),
        json={**payload, "type_ids": [str(association_id), str(producer_id)]},
    )
    assert multiple.status_code == 400

    created = client.post(
        "/api/exhibitors",
        headers=auth(token),
        json={**payload, "nombre_tipo_expositor": "Asociación Mujeres Productoras"},
    )
    assert created.status_code == 201
    assert created.json["data"]["type_ids"] == [str(association_id)]
    assert created.json["data"]["tipos_expositor"] == ["Asociación"]
    assert created.json["data"]["nombre_tipo_expositor"] == "Asociación Mujeres Productoras"


def test_admin_crea_feria_sin_portada_y_auditoria_muestra_usuario(app, client):
    with app.app_context():
        _, token = admin_token(client)
        start = bolivia_today() + timedelta(days=30)

    response = client.post(
        "/api/fairs",
        headers=auth(token),
        json={
            "nombre": "Feria con URL",
            "lugar": "Plaza principal",
            "departamento": "Cochabamba",
            "fecha_inicio": start.isoformat(),
            "fecha_fin": (start + timedelta(days=2)).isoformat(),
        },
    )

    assert response.status_code == 201
    assert response.json["imagen_portada"] is None
    unchanged_fair = client.patch(
        f"/api/fairs/{response.json['id']}",
        headers=auth(token),
        json=response.json,
    )
    assert unchanged_fair.status_code == 200, unchanged_fair.json
    audits = client.get("/api/audit", headers=auth(token))
    assert audits.status_code == 200
    assert any(item["usuario"] == "superadmin" for item in audits.json["items"])
    assert all(item["descripcion"].strip() for item in audits.json["items"])


def test_sincronizacion_publica_feria_segun_fechas(app, client):
    with app.app_context():
        admin_id, token = admin_token(client)
        today = bolivia_today()
        first = Fair(
            nombre="Feria Uno",
            slug="feria-uno",
            lugar="Plaza",
            departamento="La Paz",
            fecha_inicio=today,
            fecha_fin=today + timedelta(days=1),
            imagen_portada=None,
            estado=FeriaStatus.DRAFT,
            visible_publicamente=False,
            created_by=admin_id,
        )
        second = Fair(
            nombre="Feria Dos",
            slug="feria-dos",
            lugar="Campo",
            departamento="Cochabamba",
            fecha_inicio=today + timedelta(days=3),
            fecha_fin=today + timedelta(days=4),
            imagen_portada=None,
            estado=FeriaStatus.DRAFT,
            visible_publicamente=False,
            created_by=admin_id,
        )
        db.session.add_all([first, second])
        db.session.commit()
        first_id, second_id = first.id, second.id

    response = client.get("/api/fairs", headers=auth(token))
    assert response.status_code == 200

    with app.app_context():
        saved_first = db.session.get(Fair, first_id)
        saved_second = db.session.get(Fair, second_id)
        assert saved_first.estado == FeriaStatus.PUBLISHED
        assert saved_first.visible_publicamente is True
        assert saved_second.estado == FeriaStatus.DRAFT
        assert saved_second.visible_publicamente is False


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
        today = bolivia_today()
        fair = Fair(
            nombre="Feria",
            slug="feria",
            lugar="Plaza",
            departamento="La Paz",
            fecha_inicio=today,
            fecha_fin=today + timedelta(days=1),
            imagen_portada=None,
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


def test_admin_no_puede_crear_productos(app, client):
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
    assert response.status_code == 403
    assert "solo pueden ser creados" in response.json["error"]

    with app.app_context():
        assert db.session.query(Product).count() == 0
