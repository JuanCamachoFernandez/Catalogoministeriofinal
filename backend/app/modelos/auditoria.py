from ..extensiones import db
from .base import now, uid


class Audit(db.Model):
    __tablename__ = "auditorias"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    user_id = db.Column("usuario_id", db.Uuid, db.ForeignKey("usuarios.id"), index=True)
    accion = db.Column(db.String(100), nullable=False, index=True)
    entidad = db.Column(db.String(100), nullable=False)
    entidad_id = db.Column(db.Uuid)
    descripcion = db.Column(db.Text, nullable=False)
    resultado = db.Column(db.String(30), nullable=False, default="SUCCESS")
    datos_anteriores = db.Column(db.JSON)
    datos_nuevos = db.Column(db.JSON)
    ip_address = db.Column("direccion_ip", db.String(45))
    user_agent = db.Column("agente_usuario", db.String(500))
    created_at = db.Column(
        "fecha_creacion",
        db.DateTime(timezone=True),
        default=now,
        nullable=False,
        index=True,
    )
