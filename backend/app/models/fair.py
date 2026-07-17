from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy import CheckConstraint, UniqueConstraint, select, text

from ..extensions import db
from .base import TimestampMixin, now, uid
from .enums import AssignmentStatus, FeriaStatus

BOLIVIA_TZ = ZoneInfo("America/La_Paz")


def bolivia_today():
    return now().astimezone(BOLIVIA_TZ).date()


class Fair(TimestampMixin, db.Model):
    __tablename__ = "fairs"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    nombre = db.Column(db.String(200), nullable=False, index=True)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    descripcion = db.Column(db.Text)
    lugar = db.Column(db.String(200), nullable=False)
    direccion = db.Column(db.String(255))
    departamento = db.Column(db.String(80), nullable=False, index=True)
    municipio = db.Column(db.String(100), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.Time)
    hora_fin = db.Column(db.Time)
    fecha_limite_registro = db.Column(db.Date)
    imagen_portada = db.Column(db.String(500), nullable=True)
    observaciones = db.Column(db.Text)
    estado = db.Column(
        db.Enum(FeriaStatus, name="fair_status"),
        nullable=False,
        default=FeriaStatus.DRAFT,
    )
    visible_publicamente = db.Column(db.Boolean, nullable=False, default=False)
    created_by = db.Column(db.Uuid, db.ForeignKey("users.id"), nullable=False)
    deleted_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("fecha_fin >= fecha_inicio", name="ck_fair_dates"),
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
    def has_overlap(cls, start, end, exclude_id=None):
        query = select(cls.id).where(
            cls.deleted_at.is_(None),
            cls.estado.notin_([FeriaStatus.FINISHED, FeriaStatus.DISABLED]),
            cls.fecha_inicio <= end,
            cls.fecha_fin >= start,
        )
        if exclude_id:
            query = query.where(cls.id != exclude_id)
        return db.session.scalar(query) is not None

    @classmethod
    def acquire_schedule_lock(cls):
        if db.session.get_bind().dialect.name == "postgresql":
            db.session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": 182736451},
            )

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
            query = query.where(cls.nombre.ilike(f"%{term}%"))
        if status:
            query = query.where(cls.estado == status)
        return query


class FairImage(db.Model):
    __tablename__ = "fair_images"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    fair_id = db.Column(
        db.Uuid, db.ForeignKey("fairs.id", ondelete="CASCADE"), nullable=False
    )
    filename = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    alt_text = db.Column(db.String(255))
    is_cover = db.Column(db.Boolean, default=False)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=now, nullable=False)


class FairExhibitor(TimestampMixin, db.Model):
    __tablename__ = "fair_exhibitors"
    id = db.Column(db.Uuid, primary_key=True, default=uid)
    fair_id = db.Column(db.Uuid, db.ForeignKey("fairs.id"), nullable=False)
    exhibitor_id = db.Column(db.Uuid, db.ForeignKey("exhibitors.id"), nullable=False)
    estado = db.Column(
        db.Enum(AssignmentStatus, name="assignment_status"),
        nullable=False,
        default=AssignmentStatus.PENDING,
    )
    numero_stand = db.Column(db.String(40))
    sector = db.Column(db.String(100))
    observaciones = db.Column(db.Text)
    authorized_by = db.Column(db.Uuid, db.ForeignKey("users.id"))
    authorized_at = db.Column(db.DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("fair_id", "exhibitor_id", name="uq_fair_exhibitor"),
    )

    @classmethod
    def for_fair_query(cls, fair_id):
        return select(cls).where(cls.fair_id == fair_id)

    @classmethod
    def public_exhibitors_query(cls, fair_id, term=None, department=None):
        from .exhibitor import Exhibitor
        from .enums import UserStatus

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
        from .exhibitor import Exhibitor
        from .enums import UserStatus

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
