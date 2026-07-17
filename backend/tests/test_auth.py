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


def test_recuperacion_usa_token_una_sola_vez(app, client):
    with app.app_context():
        create_user()
    requested = client.post(
        "/api/auth/forgot-password", json={"email": "admin.prueba@gmail.com"}
    )
    token = requested.json["reset_token"]
    payload = {"token": token, "new_password": "Recuperada2026!"}
    assert client.post("/api/auth/reset-password", json=payload).status_code == 200
    assert client.post("/api/auth/reset-password", json=payload).status_code == 400
