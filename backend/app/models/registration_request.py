from sqlalchemy import Index, UniqueConstraint

from ..extensions import db
from .base import TimestampMixin, uid
from .enums import NotificationStatus, RegistrationStatus


class RegistrationRequest(TimestampMixin, db.Model):
    __tablename__ = "solicitudes_registro"

    id = db.Column(db.Uuid, primary_key=True, default=uid)
    nombre_comercial = db.Column(db.String(200), nullable=False)
    razon_social = db.Column(db.String(200), nullable=False)
    nit = db.Column(db.String(50))
    registro_seprec = db.Column(db.String(100))
    registro_pro_bolivia = db.Column(db.String(100))
    nombre_representante = db.Column(db.String(200), nullable=False)
    departamento = db.Column(db.String(80), nullable=False)
    direccion_fisica = db.Column(db.String(255), nullable=False)
    telefono_whatsapp = db.Column(db.String(30), nullable=False)
    correo_electronico = db.Column(db.String(255), nullable=False, index=True)
    facebook_url = db.Column(db.String(500))
    instagram_url = db.Column(db.String(500))
    tiktok_url = db.Column(db.String(500))
    resena_comercial = db.Column(db.Text, nullable=False)
    logo_url = db.Column(db.String(500))
    estado = db.Column(
        db.Enum(RegistrationStatus, name="estado_solicitud_registro"),
        nullable=False,
        default=RegistrationStatus.PENDING,
        index=True,
    )
    fecha_revision = db.Column(db.DateTime(timezone=True))
    observaciones = db.Column(db.Text)
    motivo_rechazo = db.Column(db.Text)
    reviewed_by = db.Column(db.Uuid, db.ForeignKey("usuarios.id"))
    credentials_sent_at = db.Column(db.DateTime(timezone=True))
    notification_status = db.Column(
        db.Enum(NotificationStatus, name="estado_notificacion_solicitud")
    )
    __table_args__ = (
        Index(
            "solicitud_pendiente_correo_unica",
            "correo_electronico",
            unique=True,
            postgresql_where=(estado == RegistrationStatus.PENDING),
            sqlite_where=(estado == RegistrationStatus.PENDING),
        ),
        Index(
            "solicitud_pendiente_nit_unica",
            "nit",
            unique=True,
            postgresql_where=((estado == RegistrationStatus.PENDING) & (nit.is_not(None))),
            sqlite_where=((estado == RegistrationStatus.PENDING) & (nit.is_not(None))),
        ),
    )


class RegistrationRequestSector(db.Model):
    __tablename__ = "sectores_solicitud_registro"

    id = db.Column(db.Uuid, primary_key=True, default=uid)
    registration_request_id = db.Column(
        db.Uuid,
        db.ForeignKey("solicitudes_registro.id", ondelete="CASCADE"),
        nullable=False,
    )
    productive_sector_id = db.Column(
        db.Uuid, db.ForeignKey("sectores_productivos.id"), nullable=False
    )
    detalle_otro = db.Column(db.String(255))
    __table_args__ = (
        UniqueConstraint(
            "registration_request_id",
            "productive_sector_id",
            name="sector_solicitud_registro_unico",
        ),
    )
