from sqlalchemy import Index, UniqueConstraint, select

from ..extensiones import db
from .base import TimestampMixin, uid
from .enumeraciones import ProductiveUnitStatus


class ProductiveUnit(TimestampMixin, db.Model):
    __tablename__ = "unidades_productivas"

    id = db.Column(db.Uuid, primary_key=True, default=uid)
    user_id = db.Column(db.Uuid, db.ForeignKey("usuarios.id"), unique=True, nullable=False)
    registration_request_id = db.Column(
        db.Uuid, db.ForeignKey("solicitudes_registro.id"), unique=True, nullable=False
    )
    nombre_comercial = db.Column(db.String(200), nullable=False, index=True)
    razon_social = db.Column(db.String(200), nullable=False)
    nit = db.Column(db.String(50), unique=True)
    registro_seprec = db.Column(db.String(100))
    registro_pro_bolivia = db.Column(db.String(100))
    nombres_representante = db.Column(db.String(100), nullable=False)
    apellido_paterno_representante = db.Column(db.String(100), nullable=False)
    apellido_materno_representante = db.Column(db.String(100), nullable=False)
    departamento = db.Column(db.String(80), nullable=False, index=True)
    direccion_fisica = db.Column(db.String(255), nullable=False)
    telefono_whatsapp = db.Column(db.String(30), nullable=False)
    correo_electronico = db.Column(db.String(255), nullable=False)
    facebook_url = db.Column(db.String(500))
    instagram_url = db.Column(db.String(500))
    tiktok_url = db.Column(db.String(500))
    resena_comercial = db.Column(db.Text, nullable=False)
    logo_url = db.Column(db.String(500))
    logo_public_id = db.Column("identificador_logo_cloudinary", db.String(500), nullable=True)
    estado = db.Column(
        db.Enum(ProductiveUnitStatus, name="estado_unidad_productiva"),
        nullable=False,
        default=ProductiveUnitStatus.ACTIVE,
        index=True,
    )
    fecha_aprobacion = db.Column(db.DateTime(timezone=True), nullable=False)
    deleted_at = db.Column("fecha_eliminacion", db.DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("correo_electronico"),
        Index("indice_unidades_productivas_correo_electronico", "correo_electronico"),
    )

    @classmethod
    def public_query(cls):
        return select(cls).where(
            cls.estado == ProductiveUnitStatus.ACTIVE, cls.deleted_at.is_(None)
        )

    @property
    def nombre_representante(self):
        return " ".join(
            filter(
                None,
                (
                    self.nombres_representante,
                    self.apellido_paterno_representante,
                    self.apellido_materno_representante,
                ),
            )
        )
