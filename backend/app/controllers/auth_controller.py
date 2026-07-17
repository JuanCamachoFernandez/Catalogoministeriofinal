from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets

from flask import Blueprint, current_app, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    jwt_required,
)
from sqlalchemy import select

from ..email_service import BrevoEmailService, EmailDeliveryError
from ..extensions import db
from ..models import PasswordRecovery, RevokedToken, User, UserStatus
from ..views import error, user_json
from .common import audit, current_user

auth_bp = Blueprint("auth", __name__)


def strong_password(value):
    return len(value) >= 10 and all(
        (
            any(char.isupper() for char in value),
            any(char.islower() for char in value),
            any(char.isdigit() for char in value),
            any(not char.isalnum() for char in value),
        )
    )


@auth_bp.post("/auth/login")
def login():
    data = request.get_json() or {}
    value = (data.get("login") or "").lower().strip()
    user = db.session.scalar(
        select(User).where((User.email == value) | (User.username == value))
    )
    if not user or user.status != UserStatus.ACTIVE or not user.check_password(
        data.get("password", "")
    ):
        if user and user.status == UserStatus.ACTIVE:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.status = UserStatus.LOCKED
            db.session.commit()
        return error("Credenciales inválidas", 401)
    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    return {
        "access_token": create_access_token(identity=str(user.id)),
        "user": user_json(user),
    }


@auth_bp.get("/auth/me")
@jwt_required()
def me():
    user = current_user()
    return user_json(user) if user else error("No autorizado", 401)


@auth_bp.post("/auth/change-password")
@jwt_required()
def change_password():
    user = current_user()
    data = request.get_json() or {}
    new_password = data.get("new_password", "")
    if not user or not user.check_password(data.get("current_password", "")):
        return error("La contraseña actual no es correcta")
    if not strong_password(new_password):
        return error("La contraseña no cumple los requisitos")
    if user.check_password(new_password):
        return error("No puede reutilizar la contraseña")
    user.set_password(new_password)
    user.must_change_password = False
    user.password_changed_at = datetime.now(timezone.utc)
    audit("CAMBIAR_CONTRASENA", "Usuario", user.id)
    db.session.commit()
    try:
        BrevoEmailService().send_password_changed(
            user.email, f"{user.first_name} {user.last_name}"
        )
    except EmailDeliveryError:
        current_app.logger.exception("No se pudo enviar confirmación de contraseña")
    return {"message": "Contraseña actualizada"}


@auth_bp.post("/auth/logout")
@jwt_required()
def logout():
    token = get_jwt()
    db.session.add(
        RevokedToken(
            jti=token["jti"],
            expires_at=datetime.fromtimestamp(token["exp"], tz=timezone.utc),
        )
    )
    db.session.commit()
    return {"message": "Sesión cerrada"}


@auth_bp.post("/auth/forgot-password")
def forgot_password():
    data = request.get_json() or {}
    value = (data.get("email") or data.get("login") or "").lower().strip()
    user = db.session.scalar(
        select(User).where((User.email == value) | (User.username == value))
    )
    response = {"message": "Si la cuenta existe, se enviaron instrucciones"}
    if not user or user.status == UserStatus.INACTIVE:
        return response
    raw_token = secrets.token_urlsafe(32)
    recovery = PasswordRecovery(
        user_id=user.id,
        token_hash=sha256(raw_token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db.session.add(recovery)
    db.session.commit()
    reset_url = f"{current_app.config['FRONTEND_URL']}/gestion/restablecer-contrasena?token={raw_token}"
    try:
        BrevoEmailService().send_password_reset(
            user.email, f"{user.first_name} {user.last_name}", reset_url
        )
    except EmailDeliveryError:
        current_app.logger.exception("No se pudo enviar recuperación de contraseña")
    if current_app.config.get("TESTING"):
        response["reset_token"] = raw_token
    return response


@auth_bp.post("/auth/reset-password")
def reset_password():
    data = request.get_json() or {}
    token = data.get("token") or ""
    password = data.get("new_password") or ""
    if not token or not strong_password(password):
        return error("Token y contraseña válida son obligatorios")
    recovery = db.session.scalar(
        select(PasswordRecovery).where(
            PasswordRecovery.token_hash == sha256(token.encode()).hexdigest(),
            PasswordRecovery.used_at.is_(None),
        )
    )
    now = datetime.now(timezone.utc)
    expires_at = recovery.expires_at if recovery else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not recovery or expires_at <= now:
        return error("El token es inválido o expiró", 400)
    user = db.session.get(User, recovery.user_id)
    user.set_password(password)
    user.must_change_password = False
    user.failed_login_attempts = 0
    user.status = UserStatus.ACTIVE
    user.password_changed_at = now
    recovery.used_at = now
    audit("RESTABLECER_CONTRASENA", "Usuario", user.id)
    db.session.commit()
    return {"message": "Contraseña restablecida"}
