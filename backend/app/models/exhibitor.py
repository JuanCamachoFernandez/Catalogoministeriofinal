from sqlalchemy import UniqueConstraint, select

from ..extensions import db
from .base import TimestampMixin, uid
from .enums import DocumentType, UserStatus


class Exhibitor(TimestampMixin, db.Model):
    __tablename__ = "expositores"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    user_id = db.Column(
        "usuario_id", db.Uuid, db.ForeignKey("usuarios.id"), unique=True, nullable=False
    )
    nombre_comercial = db.Column(db.String(200), nullable=False, index=True)
    tipo_documento = db.Column(
        db.Enum(DocumentType, name="tipo_documento"), nullable=False
    )
    numero_documento = db.Column(db.String(50), unique=True, nullable=False)
    nombre_responsable = db.Column(db.String(100), nullable=False)
    apellido_responsable = db.Column(db.String(100), nullable=False)
    apellido_paterno_responsable = db.Column(db.String(100))
    apellido_materno_responsable = db.Column(db.String(100))
    telefono_whatsapp = db.Column("celular_whatsapp", db.String(11), nullable=False)
    correo = db.Column(db.String(255), unique=True, nullable=False)
    departamento = db.Column(db.String(80), nullable=False, index=True)
    municipio = db.Column(db.String(100), nullable=False, index=True)
    direccion = db.Column(db.String(255))
    descripcion = db.Column(db.Text)
    descripcion_productos = db.Column(db.Text)
    nombre_tipo_expositor = db.Column(db.String(200))
    logo = db.Column(db.String(500))
    estado = db.Column(
        db.Enum(UserStatus, name="estado_expositor"),
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    deleted_at = db.Column("fecha_eliminacion", db.DateTime(timezone=True))
    user = db.relationship("User", backref=db.backref("exhibitor", uselist=False))

    @classmethod
    def admin_query(cls, term=None, department=None, status=None):
        query = select(cls).where(cls.deleted_at.is_(None))
        if term:
            query = query.where(
                cls.nombre_comercial.ilike(f"%{term}%")
                | cls.nombre_responsable.ilike(f"%{term}%")
                | cls.apellido_responsable.ilike(f"%{term}%")
                | cls.apellido_paterno_responsable.ilike(f"%{term}%")
                | cls.apellido_materno_responsable.ilike(f"%{term}%")
                | cls.correo.ilike(f"%{term}%")
                | cls.numero_documento.ilike(f"%{term}%")
            )
        if department:
            query = query.where(cls.departamento == department)
        if status:
            query = query.where(cls.estado == status)
        return query


class ExhibitorType(TimestampMixin, db.Model):
    __tablename__ = "tipos_expositor"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    estado = db.Column(db.Boolean, default=True, nullable=False)


class ExhibitorTypeLink(db.Model):
    __tablename__ = "tipos_expositor_asignados"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    exhibitor_id = db.Column(
        "expositor_id",
        db.Uuid,
        db.ForeignKey("expositores.id", ondelete="CASCADE"),
        nullable=False,
    )
    type_id = db.Column(
        "tipo_expositor_id", db.Uuid, db.ForeignKey("tipos_expositor.id"), nullable=False
    )
    __table_args__ = (
        UniqueConstraint(
            "expositor_id",
            "tipo_expositor_id",
            name="tipo_expositor_asignado_unico",
        ),
    )
