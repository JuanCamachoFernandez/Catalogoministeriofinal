from datetime import datetime, timezone
from unittest.mock import patch

from app.extensiones import db
from app.modelos import (
    Audit,
    PasswordRecovery,
    ProductiveUnit,
    ProductiveUnitStatus,
    RegistrationRequest,
    RegistrationStatus,
    Role,
    User,
    UserStatus,
)


def create_user():
    user = User(
        username="admin.prueba",
        email="admin.prueba@gmail.com",
        role=Role.ADMIN,
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
        assert user.role == Role.ADMIN
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


def test_login_bloquea_y_audita_al_alcanzar_el_limite(app, client):
    with app.app_context():
        user = create_user()
        user.must_change_password = False
        db.session.commit()
        user_id = user.id

    for _ in range(app.config["LIMITE_INTENTOS_FALLIDOS"]):
        response = client.post(
            "/api/auth/login",
            json={"login": "admin.prueba", "password": "Incorrecta2026!"},
        )
        assert response.status_code == 401

    with app.app_context():
        saved = db.session.get(User, user_id)
        assert saved.status == UserStatus.LOCKED
        assert saved.blocked_until is not None
        assert db.session.scalar(
            db.select(Audit.id).where(
                Audit.user_id == user_id,
                Audit.accion == "BLOQUEAR",
            )
        )


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
    refresh_token = login.json["refresh_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401
    assert client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"},
    ).status_code == 401


def test_logout_con_refresh_token_invalida_toda_la_sesion(app, client):
    with app.app_context():
        user = create_user()
        user.must_change_password = False
        db.session.commit()
    login = client.post(
        "/api/auth/login",
        json={"login": "admin.prueba", "password": "Temporal2026!"},
    )
    access_token = login.json["access_token"]
    refresh_token = login.json["refresh_token"]

    response = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == 200
    assert client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    ).status_code == 401
    assert client.post(
        "/api/auth/refresh",
        headers={"Authorization": f"Bearer {refresh_token}"},
    ).status_code == 401


def test_token_de_cuenta_inactiva_o_eliminada_se_rechaza_inmediatamente(app, client):
    with app.app_context():
        user = create_user()
        user.must_change_password = False
        db.session.commit()
        user_id = user.id
    login = client.post(
        "/api/auth/login",
        json={"login": "admin.prueba", "password": "Temporal2026!"},
    )
    headers = {"Authorization": f"Bearer {login.json['access_token']}"}

    with app.app_context():
        user = db.session.get(User, user_id)
        user.status = UserStatus.INACTIVE
        db.session.commit()
    assert client.get("/api/auth/me", headers=headers).status_code == 401

    with app.app_context():
        user = db.session.get(User, user_id)
        user.status = UserStatus.ACTIVE
        user.deleted_at = datetime.now(timezone.utc)
        db.session.commit()
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


def test_recuperacion_rechaza_correos_sin_cuenta_activa_y_no_envia_mensajes(app, client):
    generic_message = "Si la cuenta existe, enviaremos un codigo de recuperacion al correo registrado"
    with patch(
        "app.rutas.autenticacion.BrevoEmailService.send_password_code"
    ) as send_password_code:
        missing = client.post(
            "/api/auth/forgot-password", json={"email": "inexistente@gmail.com"}
        )
        assert missing.status_code == 200
        assert missing.json["message"] == generic_message

        with app.app_context():
            user = create_user()
            user_id = user.id

        for status in (UserStatus.INACTIVE, UserStatus.LOCKED, UserStatus.BLOCKED):
            with app.app_context():
                user = db.session.get(User, user_id)
                user.status = status
                user.deleted_at = None
                db.session.commit()
            response = client.post(
                "/api/auth/forgot-password",
                json={"email": "admin.prueba@gmail.com"},
            )
            assert response.status_code == 200
            assert response.json["message"] == generic_message

        with app.app_context():
            user = db.session.get(User, user_id)
            user.status = UserStatus.ACTIVE
            user.deleted_at = datetime.now(timezone.utc)
            db.session.commit()
        deleted = client.post(
            "/api/auth/forgot-password",
            json={"email": "admin.prueba@gmail.com"},
        )
        assert deleted.status_code == 200
        assert deleted.json["message"] == generic_message

        send_password_code.assert_not_called()
        with app.app_context():
            assert db.session.scalar(db.select(db.func.count(PasswordRecovery.id))) == 0


def test_recuperacion_de_unidad_productiva_exige_solicitud_aprobada_y_unidad_activa(app, client):
    with app.app_context():
        user = User(
            username="unidad.pendiente",
            email="unidad.pendiente@gmail.com",
            role=Role.PRODUCTIVE_UNIT_RESPONSIBLE,
            first_name="Ana",
            last_name="Quispe",
            status=UserStatus.ACTIVE,
        )
        user.set_password("Temporal2026!")
        registration = RegistrationRequest(
            nombre_comercial="Manos Andinas",
            razon_social="Manos Andinas SRL",
            nombres_representante="Ana",
            apellido_paterno_representante="Quispe",
            apellido_materno_representante="Mamani",
            departamento="La Paz",
            direccion_fisica="Calle 1",
            telefono_whatsapp="71234567",
            correo_electronico=user.email,
            resena_comercial="Artesanía boliviana",
            estado=RegistrationStatus.PENDING,
        )
        db.session.add_all([user, registration])
        db.session.flush()
        unit = ProductiveUnit(
            user_id=user.id,
            registration_request_id=registration.id,
            nombre_comercial=registration.nombre_comercial,
            razon_social=registration.razon_social,
            nombres_representante=registration.nombres_representante,
            apellido_paterno_representante=registration.apellido_paterno_representante,
            apellido_materno_representante=registration.apellido_materno_representante,
            departamento=registration.departamento,
            direccion_fisica=registration.direccion_fisica,
            telefono_whatsapp=registration.telefono_whatsapp,
            correo_electronico=registration.correo_electronico,
            resena_comercial=registration.resena_comercial,
            estado=ProductiveUnitStatus.ACTIVE,
            fecha_aprobacion=datetime.now(timezone.utc),
        )
        db.session.add(unit)
        db.session.commit()
        registration_id = registration.id
        unit_id = unit.id

    with patch(
        "app.rutas.autenticacion.BrevoEmailService.send_password_code",
        return_value={"sent": True},
    ) as send_password_code:
        pending = client.post(
            "/api/auth/forgot-password",
            json={"email": "unidad.pendiente@gmail.com"},
        )
        assert pending.status_code == 200
        send_password_code.assert_not_called()

        with app.app_context():
            registration = db.session.get(RegistrationRequest, registration_id)
            registration.estado = RegistrationStatus.APPROVED
            db.session.commit()
        approved = client.post(
            "/api/auth/forgot-password",
            json={"email": "unidad.pendiente@gmail.com"},
        )
        assert approved.status_code == 200
        assert "recovery_code" in approved.json
        send_password_code.assert_called_once()

        with app.app_context():
            unit = db.session.get(ProductiveUnit, unit_id)
            unit.estado = ProductiveUnitStatus.INACTIVE
            db.session.commit()
        inactive = client.post(
            "/api/auth/forgot-password",
            json={"email": "unidad.pendiente@gmail.com"},
        )
        assert inactive.status_code == 200
        assert send_password_code.call_count == 1


def test_recuperacion_se_detiene_si_la_cuenta_deja_de_estar_activa(app, client):
    with app.app_context():
        user = create_user()
        user_id = user.id

    with patch(
        "app.rutas.autenticacion.BrevoEmailService.send_password_code",
        return_value={"sent": True},
    ):
        requested = client.post(
            "/api/auth/forgot-password", json={"email": "admin.prueba@gmail.com"}
        )
    code = requested.json["recovery_code"]
    with app.app_context():
        user = db.session.get(User, user_id)
        user.status = UserStatus.INACTIVE
        db.session.commit()

    verified = client.post(
        "/api/auth/verify-recovery-code",
        json={"email": "admin.prueba@gmail.com", "code": code},
    )
    assert verified.status_code == 400
    assert verified.json["error"] == "Codigo invalido o expirado"

    with app.app_context():
        user = db.session.get(User, user_id)
        user.status = UserStatus.ACTIVE
        db.session.commit()
    with patch(
        "app.rutas.autenticacion.BrevoEmailService.send_password_code",
        return_value={"sent": True},
    ):
        requested = client.post(
            "/api/auth/forgot-password", json={"email": "admin.prueba@gmail.com"}
        )
    verified = client.post(
        "/api/auth/verify-recovery-code",
        json={
            "email": "admin.prueba@gmail.com",
            "code": requested.json["recovery_code"],
        },
    )
    with app.app_context():
        user = db.session.get(User, user_id)
        user.status = UserStatus.INACTIVE
        db.session.commit()
    reset = client.post(
        "/api/auth/reset-password",
        json={
            "token": verified.json["reset_token"],
            "new_password": "Recuperada2026!",
        },
    )
    assert reset.status_code == 400
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user.status == UserStatus.INACTIVE
        assert user.check_password("Temporal2026!") is True


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
