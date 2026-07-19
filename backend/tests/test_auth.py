from app.extensions import db
from app.models import Role, User, UserStatus


def create_user():
    user = User(
        username="admin.prueba",
        email="admin.prueba@gmail.com",
        role=Role.SUPERADMIN,
        first_name="Admin",
        last_name="Prueba",
        status=UserStatus.ACTIVE,
        must_change_password=True,
    )
    user.set_password("Temporal2026!")
    db.session.add(user)
    db.session.commit()
    return user


def test_seed_admin_lee_identidad_completa_desde_entorno(app, monkeypatch):
    monkeypatch.setenv("USUARIO_ADMINISTRADOR_INICIAL", "rosa.quispe")
    monkeypatch.setenv("NOMBRES_ADMINISTRADOR_INICIAL", "Rosa María")
    monkeypatch.setenv("APELLIDO_PATERNO_ADMINISTRADOR_INICIAL", "Quispe")
    monkeypatch.setenv("APELLIDO_MATERNO_ADMINISTRADOR_INICIAL", "Mamani")
    monkeypatch.setenv("CORREO_ADMINISTRADOR_INICIAL", "rosa.quispe@gmail.com")
    monkeypatch.setenv("CONTRASENA_ADMINISTRADOR_INICIAL", "InicialSegura2026!")

    result = app.test_cli_runner().invoke(args=["seed-admin"])
    assert result.exit_code == 0
    with app.app_context():
        user = db.session.scalar(
            db.select(User).where(User.username == "rosa.quispe")
        )
        assert user is not None
        assert user.role == Role.SUPERADMIN
        assert user.first_name == "Rosa María"
        assert user.apellido_paterno == "Quispe"
        assert user.apellido_materno == "Mamani"
        assert user.email == "rosa.quispe@gmail.com"
        assert user.check_password("InicialSegura2026!") is True


def test_primer_ingreso_obliga_cambio_y_actualiza_password(app, client):
    with app.app_context():
        user = create_user()
        user_id = user.id

    login = client.post(
        "/api/auth/login",
        json={"login": "admin.prueba", "password": "Temporal2026!"},
    )
    assert login.status_code == 200
    assert login.json["user"]["must_change_password"] is True
    token = login.json["access_token"]

    changed = client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": "Temporal2026!",
            "new_password": "Definitiva2026!",
        },
    )
    assert changed.status_code == 200
    with app.app_context():
        saved = db.session.get(User, user_id)
        assert saved.must_change_password is False
        assert saved.check_password("Definitiva2026!") is True


def test_login_rechaza_password_incorrecta(app, client):
    with app.app_context():
        create_user()
    response = client.post(
        "/api/auth/login",
        json={"login": "admin.prueba", "password": "incorrecta"},
    )
    assert response.status_code == 401


def test_reautenticacion_exige_password_actual(app, client):
    with app.app_context():
        user = create_user()
        user.must_change_password = False
        db.session.commit()
    login = client.post(
        "/api/auth/login",
        json={"login": "admin.prueba", "password": "Temporal2026!"},
    )
    headers = {"Authorization": f"Bearer {login.json['access_token']}"}
    invalid = client.post(
        "/api/auth/reauthenticate",
        headers=headers,
        json={"current_password": "Incorrecta"},
    )
    assert invalid.status_code == 401
    valid = client.post(
        "/api/auth/reauthenticate",
        headers=headers,
        json={"current_password": "Temporal2026!"},
    )
    assert valid.status_code == 200


def test_login_no_acepta_correo_como_usuario(app, client):
    with app.app_context():
        create_user()

    response = client.post(
        "/api/auth/login",
        json={"login": "admin.prueba@gmail.com", "password": "Temporal2026!"},
    )

    assert response.status_code == 401


def test_logout_revoca_token(app, client):
    with app.app_context():
        user = create_user()
        user.must_change_password = False
        db.session.commit()
    login = client.post(
        "/api/auth/login",
        json={"login": "admin.prueba", "password": "Temporal2026!"},
    )
    token = login.json["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_recuperacion_verifica_codigo_y_usa_token_una_sola_vez(app, client):
    with app.app_context():
        create_user()
    requested = client.post(
        "/api/auth/forgot-password", json={"email": "admin.prueba@gmail.com"}
    )
    code = requested.json["recovery_code"]
    assert len(code) == 6
    assert code.isdigit()
    wrong_code = "999999" if code != "999999" else "888888"
    direct = client.post(
        "/api/auth/reset-password",
        json={"token": code, "new_password": "Recuperada2026!"},
    )
    assert direct.status_code == 400
    invalid = client.post(
        "/api/auth/verify-recovery-code",
        json={"email": "admin.prueba@gmail.com", "code": wrong_code},
    )
    assert invalid.status_code == 400
    verified = client.post(
        "/api/auth/verify-recovery-code",
        json={"email": "admin.prueba@gmail.com", "code": code},
    )
    assert verified.status_code == 200
    token = verified.json["reset_token"]
    payload = {"token": token, "new_password": "Recuperada2026!"}
    assert client.post("/api/auth/reset-password", json=payload).status_code == 200
    assert client.post("/api/auth/reset-password", json=payload).status_code == 400


def test_codigo_recuperacion_se_bloquea_tras_cinco_intentos(app, client):
    with app.app_context():
        create_user()
    requested = client.post(
        "/api/auth/forgot-password", json={"email": "admin.prueba@gmail.com"}
    )
    code = requested.json["recovery_code"]
    wrong_code = "999999" if code != "999999" else "888888"
    for _ in range(5):
        response = client.post(
            "/api/auth/verify-recovery-code",
            json={"email": "admin.prueba@gmail.com", "code": wrong_code},
        )
        assert response.status_code == 400
    blocked = client.post(
        "/api/auth/verify-recovery-code",
        json={"email": "admin.prueba@gmail.com", "code": code},
    )
    assert blocked.status_code == 400
