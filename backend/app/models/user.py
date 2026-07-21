from argon2 import PasswordHasher
from sqlalchemy import select

from ..extensions import db
from .base import TimestampMixin, now, uid
from .enums import Role, UserStatus

ph = PasswordHasher()


class User(TimestampMixin, db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    username = db.Column("usuario", db.String(80), unique=True, nullable=False, index=True)
    email = db.Column("correo", db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column("contrasena_cifrada", db.Text, nullable=False)
    role = db.Column("rol", db.Enum(Role, name="rol_usuario"), nullable=False)
    first_name = db.Column("nombres", db.String(100), nullable=False)
    last_name = db.Column("apellidos", db.String(100), nullable=False)
    apellido_paterno = db.Column(db.String(100))
    apellido_materno = db.Column(db.String(100))
    phone = db.Column("celular", db.String(15))
    foto_perfil = db.Column(db.String(500))
    status = db.Column(
        "estado",
        db.Enum(UserStatus, name="estado_usuario"),
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    must_change_password = db.Column(
        "debe_cambiar_contrasena", db.Boolean, nullable=False, default=True
    )
    failed_login_attempts = db.Column(
        "intentos_fallidos_acceso", db.Integer, nullable=False, default=0
    )
    blocked_until = db.Column("bloqueado_hasta", db.DateTime(timezone=True))
    token_version = db.Column("version_sesion", db.Integer, nullable=False, default=0)
    last_login_at = db.Column("fecha_ultimo_acceso", db.DateTime(timezone=True))
    password_changed_at = db.Column(
        "fecha_cambio_contrasena", db.DateTime(timezone=True)
    )
    deleted_at = db.Column("fecha_eliminacion", db.DateTime(timezone=True))

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
            cls.role.in_([
                Role.SUPERADMIN,
                Role.ADMIN_VICEMINISTERIO,
                Role.ADMIN,
                Role.PRODUCTIVE_UNIT_RESPONSIBLE,
            ]),
            cls.deleted_at.is_(None),
        )
        if term:
            query = query.where(
                cls.first_name.ilike(f"%{term}%")
                | cls.last_name.ilike(f"%{term}%")
                | cls.apellido_paterno.ilike(f"%{term}%")
                | cls.apellido_materno.ilike(f"%{term}%")
                | cls.email.ilike(f"%{term}%")
            )
        return query


class AdminProfile(db.Model):
    __tablename__ = "perfiles_administradores"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    user_id = db.Column(
        "usuario_id",
        db.Uuid,
        db.ForeignKey("usuarios.id"),
        unique=True,
        nullable=False,
    )
    numero_documento = db.Column(db.String(50), unique=True)
    cargo = db.Column(db.String(150))
    unidad = db.Column(db.String(150))
    observaciones = db.Column(db.Text)
    user = db.relationship(
        "User", backref=db.backref("admin_profile", uselist=False)
    )


class AdminUnit(db.Model):
    __tablename__ = "unidades_administrativas"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    nombre = db.Column(db.String(150), unique=True, nullable=False)


class PasswordRecovery(db.Model):
    __tablename__ = "recuperaciones_contrasena"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    user_id = db.Column(
        "usuario_id", db.Uuid, db.ForeignKey("usuarios.id"), nullable=False, index=True
    )
    token_hash = db.Column("codigo_cifrado", db.String(64), unique=True, nullable=False)
    expires_at = db.Column("fecha_expiracion", db.DateTime(timezone=True), nullable=False)
    verified_at = db.Column("fecha_verificacion", db.DateTime(timezone=True))
    failed_attempts = db.Column(
        "intentos_fallidos", db.Integer, nullable=False, default=0
    )
    used_at = db.Column("fecha_uso", db.DateTime(timezone=True))
    created_at = db.Column(
        "fecha_creacion", db.DateTime(timezone=True), default=now, nullable=False
    )


class RevokedToken(db.Model):
    __tablename__ = "codigos_acceso_revocados"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    jti = db.Column(
        "identificador_codigo_acceso",
        db.String(36),
        unique=True,
        nullable=False,
        index=True,
    )
    expires_at = db.Column("fecha_expiracion", db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(
        "fecha_creacion", db.DateTime(timezone=True), default=now, nullable=False
    )
