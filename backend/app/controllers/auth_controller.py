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
from ..views import error, user_json, validate_json, validated_json
from ..views.auth_view import (
    ChangePasswordSchema,
    ForgotPasswordSchema,
    LoginSchema,
    ReauthenticateSchema,
    ResetPasswordSchema,
    VerifyRecoveryCodeSchema,
)
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
@validate_json(LoginSchema())
def login():
    data = validated_json()
    value = (data.get("login") or "").lower().strip()
    user = db.session.scalar(select(User).where(User.username == value))
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
    if not user or user.deleted_at or user.status != UserStatus.ACTIVE:
        return error("Cuenta no disponible", 403)
    return user_json(user)


@auth_bp.post("/auth/reauthenticate")
@jwt_required()
@validate_json(ReauthenticateSchema())
def reauthenticate():
    user = current_user()
    if not user or user.deleted_at or user.status != UserStatus.ACTIVE:
        return error("Cuenta no disponible", 403)
    if not user.check_password(validated_json().get("current_password", "")):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.status = UserStatus.LOCKED
        db.session.commit()
        return error("La contraseña no es correcta", 401)
    user.failed_login_attempts = 0
    audit("REAUTENTICAR", "Usuario", user.id, f"Sesión desbloqueada por {user.username}")
    db.session.commit()
    return {"message": "Sesión desbloqueada"}


@auth_bp.post("/auth/change-password")
@jwt_required()
@validate_json(ChangePasswordSchema())
def change_password():
    user = current_user()
    data = validated_json()
    new_password = data.get("new_password", "")
    if not user or user.deleted_at or user.status != UserStatus.ACTIVE:
        return error("Cuenta no disponible", 403)
    if not user.check_password(data.get("current_password", "")):
        return error("La contraseña actual no es correcta")
    if not strong_password(new_password):
        return error("La contraseña no cumple los requisitos")
    if user.check_password(new_password):
        return error("No puede reutilizar la contraseña")
    user.set_password(new_password)
    user.must_change_password = False
    user.password_changed_at = datetime.now(timezone.utc)
    audit("CAMBIAR_CONTRASENA", "Usuario", user.id, f"Contraseña cambiada por {user.username}")
    db.session.commit()
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
@validate_json(ForgotPasswordSchema())
def forgot_password():
    data = validated_json()
    value = (data.get("email") or "").lower().strip()
    user = db.session.scalar(select(User).where(User.email == value))
    response = {"message": "Si el correo está registrado, recibirá un código de 6 dígitos"}
    if not user or user.status == UserStatus.INACTIVE:
        return response
    now = datetime.now(timezone.utc)
    for previous in db.session.scalars(
        select(PasswordRecovery).where(
            PasswordRecovery.user_id == user.id,
            PasswordRecovery.used_at.is_(None),
        )
    ).all():
        previous.used_at = now
    recovery_code = f"{secrets.randbelow(1_000_000):06d}"
    recovery = PasswordRecovery(
        user_id=user.id,
        token_hash=sha256(recovery_code.encode()).hexdigest(),
        expires_at=now + timedelta(minutes=10),
    )
    db.session.add(recovery)
    db.session.commit()
    try:
        BrevoEmailService().send_password_code(
            user.email, f"{user.first_name} {user.last_name}", recovery_code
        )
    except EmailDeliveryError:
        current_app.logger.exception("No se pudo enviar recuperación de contraseña")
    if current_app.config.get("TESTING"):
        response["recovery_code"] = recovery_code
    return response


@auth_bp.post("/auth/verify-recovery-code")
@validate_json(VerifyRecoveryCodeSchema())
def verify_recovery_code():
    data = validated_json()
    email = (data.get("email") or "").lower().strip()
    user = db.session.scalar(select(User).where(User.email == email))
    recovery = None
    if user:
        recovery = db.session.scalar(
            select(PasswordRecovery)
            .where(
                PasswordRecovery.user_id == user.id,
                PasswordRecovery.used_at.is_(None),
                PasswordRecovery.verified_at.is_(None),
            )
            .order_by(PasswordRecovery.created_at.desc())
        )
    now = datetime.now(timezone.utc)
    expires_at = recovery.expires_at if recovery else None
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    code_hash = sha256((data.get("code") or "").encode()).hexdigest()
    if (
        not recovery
        or expires_at <= now
        or recovery.failed_attempts >= 5
        or not secrets.compare_digest(recovery.token_hash, code_hash)
    ):
        if recovery:
            recovery.failed_attempts += 1
            if recovery.failed_attempts >= 5:
                recovery.used_at = now
            db.session.commit()
        return error("Código inválido o expirado")
    reset_token = secrets.token_urlsafe(32)
    recovery.token_hash = sha256(reset_token.encode()).hexdigest()
    recovery.verified_at = now
    recovery.expires_at = now + timedelta(minutes=10)
    db.session.commit()
    return {"message": "Código verificado", "reset_token": reset_token}


@auth_bp.post("/auth/reset-password")
@validate_json(ResetPasswordSchema())
def reset_password():
    data = validated_json()
    token = data.get("token") or ""
    password = data.get("new_password") or ""
    if not token or not strong_password(password):
        return error("Token y contraseña válida son obligatorios")
    recovery = db.session.scalar(
        select(PasswordRecovery).where(
            PasswordRecovery.token_hash == sha256(token.encode()).hexdigest(),
            PasswordRecovery.used_at.is_(None),
            PasswordRecovery.verified_at.is_not(None),
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
    audit(
        "RESTABLECER_CONTRASENA",
        "Usuario",
        user.id,
        f"Contraseña recuperada para {user.username}",
    )
    db.session.commit()
    return {"message": "Contraseña restablecida"}
