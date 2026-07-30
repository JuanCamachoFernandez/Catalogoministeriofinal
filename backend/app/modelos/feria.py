from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy import CheckConstraint, Index, UniqueConstraint, select

from ..extensiones import db
from .base import TimestampMixin, now, uid
from .enumeraciones import AssignmentStatus, FeriaStatus

BOLIVIA_TZ = ZoneInfo("America/La_Paz")


def bolivia_today():
    return now().astimezone(BOLIVIA_TZ).date()


class Fair(TimestampMixin, db.Model):
    __tablename__ = "ferias"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    nombre = db.Column(db.String(200), nullable=False, index=True)
    slug = db.Column(
        "identificador_url", db.String(220), unique=True, nullable=False, index=True
    )
    descripcion = db.Column(db.Text)
    lugar = db.Column(db.String(200), nullable=False)
    ubicacion = db.Column(db.String(255))
    direccion = db.Column(db.String(255))
    departamento = db.Column(db.String(80), nullable=False, index=True)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.Time)
    hora_fin = db.Column(db.Time)
    fecha_limite_registro = db.Column(db.Date)
    imagen_portada = db.Column(db.String(500), nullable=True)
    imagen_portada_public_id = db.Column("identificador_portada_cloudinary", db.String(500), nullable=True)
    observaciones = db.Column(db.Text)
    estado = db.Column(
        db.Enum(FeriaStatus, name="estado_feria"),
        nullable=False,
        default=FeriaStatus.DRAFT,
    )
    visible_publicamente = db.Column(db.Boolean, nullable=False, default=False)
    created_by = db.Column(
        "creado_por_usuario_id", db.Uuid, db.ForeignKey("usuarios.id"), nullable=False
    )
    deleted_at = db.Column("fecha_eliminacion", db.DateTime(timezone=True))
    disabled_at = db.Column("fecha_desactivacion", db.DateTime(timezone=True))
    finished_at = db.Column("fecha_finalizacion", db.DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("fecha_fin >= fecha_inicio", name="fechas_validas"),
        Index("indice_ferias_estado", "estado"),
        Index("indice_ferias_fecha_inicio", "fecha_inicio"),
        Index("indice_ferias_fecha_fin", "fecha_fin"),
    )

    @property
    def terminal(self):
        return self.estado in (FeriaStatus.FINISHED, FeriaStatus.DISABLED)

    def expected_status(self, today=None):
        today = today or bolivia_today()
        if self.terminal:
            return self.estado
        if today < self.fecha_inicio:
            return FeriaStatus.DRAFT
        if today <= self.fecha_fin:
            return FeriaStatus.PUBLISHED
        return FeriaStatus.FINISHED

    @classmethod
    def active_query(cls):
        return select(cls).where(
            cls.estado == FeriaStatus.PUBLISHED,
            cls.visible_publicamente.is_(True),
            cls.deleted_at.is_(None),
        )

    @classmethod
    def lifecycle_query(cls):
        return select(cls).where(
            cls.deleted_at.is_(None),
            cls.estado.notin_([FeriaStatus.FINISHED, FeriaStatus.DISABLED]),
        )

    @classmethod
    def admin_query(cls, term=None, status=None):
        query = select(cls).where(cls.deleted_at.is_(None))
        if term:
            lookup = f"%{term}%"
            query = query.where(
                cls.nombre.ilike(lookup) | cls.ubicacion.ilike(lookup)
            )
        if status:
            query = query.where(cls.estado == status)
        return query


class FairImage(db.Model):
    __tablename__ = "imagenes_feria"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    fair_id = db.Column(
        "feria_id",
        db.Uuid,
        db.ForeignKey("ferias.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename = db.Column("nombre_archivo", db.String(255), nullable=False)
    url = db.Column("direccion_url", db.String(500), nullable=False)
    public_id = db.Column("identificador_cloudinary", db.String(500), nullable=True)
    alt_text = db.Column("texto_alternativo", db.String(255))
    is_cover = db.Column("es_portada", db.Boolean, default=False)
    display_order = db.Column("orden_visualizacion", db.Integer, default=0)
    created_at = db.Column(
        "fecha_creacion", db.DateTime(timezone=True), default=now, nullable=False
    )


class FairExhibitor(TimestampMixin, db.Model):
    __tablename__ = "expositores_feria"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    fair_id = db.Column("feria_id", db.Uuid, db.ForeignKey("ferias.id"), nullable=False)
    exhibitor_id = db.Column(
        "expositor_id", db.Uuid, db.ForeignKey("expositores.id"), nullable=False
    )
    estado = db.Column(
        db.Enum(AssignmentStatus, name="estado_asignacion"),
        nullable=False,
        default=AssignmentStatus.PENDING,
    )
    numero_stand = db.Column(db.String(40))
    sector = db.Column(db.String(100))
    observaciones = db.Column(db.Text)
    authorized_by = db.Column(
        "autorizado_por_usuario_id", db.Uuid, db.ForeignKey("usuarios.id")
    )
    authorized_at = db.Column("fecha_autorizacion", db.DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint(
            "feria_id", "expositor_id", name="expositor_feria_unico"
        ),
    )

    @classmethod
    def for_fair_query(cls, fair_id):
        return select(cls).where(cls.fair_id == fair_id)

    @classmethod
    def public_exhibitors_query(cls, fair_id, term=None, department=None):
        from .expositor import Exhibitor
        from .enumeraciones import UserStatus

        query = (
            select(Exhibitor, cls)
            .join(cls, cls.exhibitor_id == Exhibitor.id)
            .where(
                cls.fair_id == fair_id,
                cls.estado == AssignmentStatus.AUTHORIZED,
                Exhibitor.estado == UserStatus.ACTIVE,
                Exhibitor.deleted_at.is_(None),
            )
        )
        if term:
            query = query.where(Exhibitor.nombre_comercial.ilike(f"%{term}%"))
        if department:
            query = query.where(Exhibitor.departamento == department)
        return query

    @classmethod
    def public_exhibitor_query(cls, fair_slug, exhibitor_id):
        from .expositor import Exhibitor
        from .enumeraciones import UserStatus

        return (
            select(Fair, Exhibitor)
            .join(cls, cls.fair_id == Fair.id)
            .join(Exhibitor, Exhibitor.id == cls.exhibitor_id)
            .where(
                Fair.slug == fair_slug,
                Fair.estado == FeriaStatus.PUBLISHED,
                Fair.visible_publicamente.is_(True),
                Fair.deleted_at.is_(None),
                cls.exhibitor_id == exhibitor_id,
                cls.estado == AssignmentStatus.AUTHORIZED,
                Exhibitor.estado == UserStatus.ACTIVE,
                Exhibitor.deleted_at.is_(None),
            )
        )

    @classmethod
    def authorized_query(cls, fair_slug, exhibitor_id):
        return (
            select(cls)
            .join(Fair)
            .where(
                Fair.slug == fair_slug,
                Fair.estado == FeriaStatus.PUBLISHED,
                Fair.visible_publicamente.is_(True),
                Fair.deleted_at.is_(None),
                cls.exhibitor_id == exhibitor_id,
                cls.estado == AssignmentStatus.AUTHORIZED,
            )
        )
