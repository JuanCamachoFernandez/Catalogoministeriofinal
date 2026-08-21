from sqlalchemy import UniqueConstraint

from ..extensiones import db
from .base import now, uid


class FinalImportRun(db.Model):
    __tablename__ = "ejecuciones_importacion_final"

    id = db.Column(db.Uuid, primary_key=True, default=uid)
    plan_hash = db.Column(db.String(64), unique=True, nullable=False)
    general_sheet_id = db.Column(db.String(255), nullable=False)
    corrected_sheet_id = db.Column(db.String(255), nullable=False)
    general_sheet_hash = db.Column(db.String(64), nullable=False)
    corrected_sheet_hash = db.Column(db.String(64), nullable=False)
    status = db.Column("estado", db.String(30), nullable=False, default="RUNNING")
    summary = db.Column("resumen", db.JSON)
    created_at = db.Column("fecha_creacion", db.DateTime(timezone=True), default=now, nullable=False)
    finished_at = db.Column("fecha_finalizacion", db.DateTime(timezone=True))


class FinalImportSourceRow(db.Model):
    __tablename__ = "filas_fuente_importacion_final"

    id = db.Column(db.Uuid, primary_key=True, default=uid)
    run_id = db.Column(
        "ejecucion_id",
        db.Uuid,
        db.ForeignKey("ejecuciones_importacion_final.id", ondelete="CASCADE"),
        nullable=False,
    )
    source = db.Column("fuente", db.String(20), nullable=False)
    sheet_id = db.Column(db.String(255), nullable=False)
    worksheet = db.Column("hoja", db.String(255), nullable=False)
    row_number = db.Column("numero_fila", db.Integer, nullable=False)
    row_hash = db.Column("hash_fila", db.String(64), nullable=False)
    source_data = db.Column("datos_originales", db.JSON, nullable=False, default=dict)
    warnings = db.Column("advertencias", db.JSON, nullable=False, default=list)
    is_ambiguous = db.Column("es_ambiguo", db.Boolean, nullable=False, default=False)
    pending_reasons = db.Column("motivos_pendientes", db.JSON, nullable=False, default=list)
    is_pending = db.Column("es_pendiente", db.Boolean, nullable=False, default=False)
    productive_unit_id = db.Column(
        "unidad_productiva_id", db.Uuid, db.ForeignKey("unidades_productivas.id")
    )
    created_at = db.Column("fecha_creacion", db.DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (
        UniqueConstraint("ejecucion_id", "fuente", "sheet_id", "hoja", "numero_fila",
                         name="fila_fuente_importacion_unica"),
    )


class FinalImportEntityTrace(db.Model):
    __tablename__ = "entidades_importacion_final"

    id = db.Column(db.Uuid, primary_key=True, default=uid)
    source_row_id = db.Column(
        "fila_fuente_id",
        db.Uuid,
        db.ForeignKey("filas_fuente_importacion_final.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type = db.Column("tipo_entidad", db.String(40), nullable=False)
    entity_id = db.Column("entidad_id", db.Uuid, nullable=False)
    entity_key = db.Column("clave_entidad", db.String(255), nullable=False)
    drive_file_id = db.Column(db.String(255))
    created_at = db.Column("fecha_creacion", db.DateTime(timezone=True), default=now, nullable=False)
    __table_args__ = (
        UniqueConstraint("fila_fuente_id", "tipo_entidad", "clave_entidad", name="entidad_importada_unica"),
    )
