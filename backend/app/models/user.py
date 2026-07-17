from argon2 import PasswordHasher
from sqlalchemy import select

from ..extensions import db
from .base import TimestampMixin, now, uid
from .enums import Role, UserStatus

ph = PasswordHasher()


class User(TimestampMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.Enum(Role, name="user_role"), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15))
    status = db.Column(
        db.Enum(UserStatus, name="user_status"),
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    must_change_password = db.Column(db.Boolean, nullable=False, default=True)
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    last_login_at = db.Column(db.DateTime(timezone=True))
    password_changed_at = db.Column(db.DateTime(timezone=True))
    deleted_at = db.Column(db.DateTime(timezone=True))

    def set_password(self, password):
        self.password_hash = ph.hash(password)

    def check_password(self, password):
        try:
            return ph.verify(self.password_hash, password)
        except Exception:
            return False

    @classmethod
    def admin_query(cls, term=None):
        query = select(cls).where(
            cls.role.in_([Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO]),
            cls.deleted_at.is_(None),
        )
        if term:
            query = query.where(
                cls.first_name.ilike(f"%{term}%")
                | cls.last_name.ilike(f"%{term}%")
                | cls.email.ilike(f"%{term}%")
            )
        return query


class AdminProfile(db.Model):
    __tablename__ = "admin_profiles"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    user_id = db.Column(db.Uuid, db.ForeignKey("users.id"), unique=True, nullable=False)
    cargo = db.Column(db.String(150))
    unidad = db.Column(db.String(150))
    observaciones = db.Column(db.Text)
    user = db.relationship(
        "User", backref=db.backref("admin_profile", uselist=False)
    )


class PasswordRecovery(db.Model):
    __tablename__ = "password_recoveries"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    user_id = db.Column(db.Uuid, db.ForeignKey("users.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)


class RevokedToken(db.Model):
    __tablename__ = "revoked_tokens"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)
