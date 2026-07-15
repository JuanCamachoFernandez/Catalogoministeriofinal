import enum
import uuid
from datetime import datetime, timezone
from argon2 import PasswordHasher
from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from .extensions import db

ph = PasswordHasher()
def now(): return datetime.now(timezone.utc)
def uid(): return uuid.uuid4()

class Role(str, enum.Enum): SUPERADMIN="SUPERADMIN"; ADMIN_VICEMINISTERIO="ADMIN_VICEMINISTERIO"; EXPOSITOR="EXPOSITOR"
class UserStatus(str, enum.Enum): ACTIVE="ACTIVE"; INACTIVE="INACTIVE"; LOCKED="LOCKED"
class FeriaStatus(str, enum.Enum): DRAFT="DRAFT"; PUBLISHED="PUBLISHED"; DISABLED="DISABLED"; FINISHED="FINISHED"
class AssignmentStatus(str, enum.Enum): PENDING="PENDING"; AUTHORIZED="AUTHORIZED"; REJECTED="REJECTED"; REVOKED="REVOKED"
class ProductStatus(str, enum.Enum): AVAILABLE="AVAILABLE"; OUT_OF_STOCK="OUT_OF_STOCK"; INACTIVE="INACTIVE"; DELETED="DELETED"
class DocumentType(str, enum.Enum): CI="CI"; NIT="NIT"; OTRO="OTRO"

class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now, onupdate=now)

class User(TimestampMixin, db.Model):
    __tablename__="users"
    id=db.Column(db.Uuid, primary_key=True, default=uid); username=db.Column(db.String(80), unique=True, nullable=False, index=True)
    email=db.Column(db.String(255), unique=True, nullable=False, index=True); password_hash=db.Column(db.Text, nullable=False)
    role=db.Column(db.Enum(Role, name="user_role"), nullable=False); first_name=db.Column(db.String(100), nullable=False); last_name=db.Column(db.String(100), nullable=False)
    phone=db.Column(db.String(15)); status=db.Column(db.Enum(UserStatus, name="user_status"), nullable=False, default=UserStatus.ACTIVE)
    must_change_password=db.Column(db.Boolean, nullable=False, default=True); failed_login_attempts=db.Column(db.Integer, nullable=False, default=0)
    last_login_at=db.Column(db.DateTime(timezone=True)); password_changed_at=db.Column(db.DateTime(timezone=True)); deleted_at=db.Column(db.DateTime(timezone=True))
    def set_password(self,p): self.password_hash=ph.hash(p)
    def check_password(self,p):
        try: return ph.verify(self.password_hash,p)
        except Exception: return False

class AdminProfile(db.Model):
    __tablename__="admin_profiles"; id=db.Column(db.Uuid, primary_key=True, default=uid); user_id=db.Column(db.Uuid, db.ForeignKey("users.id"), unique=True, nullable=False)
    cargo=db.Column(db.String(150)); unidad=db.Column(db.String(150)); observaciones=db.Column(db.Text); user=db.relationship("User", backref=db.backref("admin_profile", uselist=False))

class Exhibitor(TimestampMixin, db.Model):
    __tablename__="exhibitors"; id=db.Column(db.Uuid, primary_key=True, default=uid); user_id=db.Column(db.Uuid,db.ForeignKey("users.id"),unique=True,nullable=False)
    nombre_comercial=db.Column(db.String(200),nullable=False,index=True); razon_social=db.Column(db.String(200)); tipo_documento=db.Column(db.Enum(DocumentType,name="document_type"),nullable=False)
    numero_documento=db.Column(db.String(50),unique=True,nullable=False); nombre_responsable=db.Column(db.String(100),nullable=False); apellido_responsable=db.Column(db.String(100),nullable=False)
    telefono_whatsapp=db.Column(db.String(11),nullable=False); email_gmail=db.Column(db.String(255),unique=True,nullable=False); departamento=db.Column(db.String(80),nullable=False,index=True)
    municipio=db.Column(db.String(100),nullable=False,index=True); direccion=db.Column(db.String(255)); descripcion=db.Column(db.Text); descripcion_productos=db.Column(db.Text)
    fotografia_perfil=db.Column(db.String(500)); estado=db.Column(db.Enum(UserStatus,name="exhibitor_status"),nullable=False,default=UserStatus.ACTIVE); deleted_at=db.Column(db.DateTime(timezone=True))
    user=db.relationship("User",backref=db.backref("exhibitor",uselist=False))

class ExhibitorType(TimestampMixin, db.Model):
    __tablename__="exhibitor_types"; id=db.Column(db.Uuid,primary_key=True,default=uid); nombre=db.Column(db.String(80),unique=True,nullable=False); estado=db.Column(db.Boolean,default=True,nullable=False)
class ExhibitorTypeLink(db.Model):
    __tablename__="exhibitor_type_links"; id=db.Column(db.Uuid,primary_key=True,default=uid); exhibitor_id=db.Column(db.Uuid,db.ForeignKey("exhibitors.id",ondelete="CASCADE"),nullable=False); type_id=db.Column(db.Uuid,db.ForeignKey("exhibitor_types.id"),nullable=False)
    __table_args__=(UniqueConstraint("exhibitor_id","type_id"),)

class Fair(TimestampMixin, db.Model):
    __tablename__="fairs"; id=db.Column(db.Uuid,primary_key=True,default=uid); nombre=db.Column(db.String(200),nullable=False,index=True); slug=db.Column(db.String(220),unique=True,nullable=False,index=True)
    descripcion=db.Column(db.Text); lugar=db.Column(db.String(200),nullable=False); direccion=db.Column(db.String(255)); departamento=db.Column(db.String(80),nullable=False,index=True); municipio=db.Column(db.String(100),nullable=False)
    fecha_inicio=db.Column(db.Date,nullable=False); fecha_fin=db.Column(db.Date,nullable=False); hora_inicio=db.Column(db.Time); hora_fin=db.Column(db.Time); fecha_limite_registro=db.Column(db.Date)
    imagen_portada=db.Column(db.String(500),nullable=False); observaciones=db.Column(db.Text); estado=db.Column(db.Enum(FeriaStatus,name="fair_status"),nullable=False,default=FeriaStatus.DRAFT)
    visible_publicamente=db.Column(db.Boolean,nullable=False,default=False); created_by=db.Column(db.Uuid,db.ForeignKey("users.id"),nullable=False); deleted_at=db.Column(db.DateTime(timezone=True))
    __table_args__=(CheckConstraint("fecha_fin >= fecha_inicio",name="ck_fair_dates"),)

class FairImage(db.Model):
    __tablename__="fair_images"; id=db.Column(db.Uuid,primary_key=True,default=uid); fair_id=db.Column(db.Uuid,db.ForeignKey("fairs.id",ondelete="CASCADE"),nullable=False); filename=db.Column(db.String(255),nullable=False); url=db.Column(db.String(500),nullable=False); alt_text=db.Column(db.String(255)); is_cover=db.Column(db.Boolean,default=False); display_order=db.Column(db.Integer,default=0); created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False)

class FairExhibitor(TimestampMixin, db.Model):
    __tablename__="fair_exhibitors"; id=db.Column(db.Uuid,primary_key=True,default=uid); fair_id=db.Column(db.Uuid,db.ForeignKey("fairs.id"),nullable=False); exhibitor_id=db.Column(db.Uuid,db.ForeignKey("exhibitors.id"),nullable=False)
    estado=db.Column(db.Enum(AssignmentStatus,name="assignment_status"),nullable=False,default=AssignmentStatus.PENDING); numero_stand=db.Column(db.String(40)); sector=db.Column(db.String(100)); observaciones=db.Column(db.Text); authorized_by=db.Column(db.Uuid,db.ForeignKey("users.id")); authorized_at=db.Column(db.DateTime(timezone=True))
    __table_args__=(UniqueConstraint("fair_id","exhibitor_id",name="uq_fair_exhibitor"),)

class Category(TimestampMixin, db.Model):
    __tablename__="categories"; id=db.Column(db.Uuid,primary_key=True,default=uid); nombre=db.Column(db.String(120),unique=True,nullable=False); slug=db.Column(db.String(140),unique=True,nullable=False); descripcion=db.Column(db.Text); estado=db.Column(db.Boolean,default=True,nullable=False); deleted_at=db.Column(db.DateTime(timezone=True))

class Product(TimestampMixin, db.Model):
    __tablename__="products"; id=db.Column(db.Uuid,primary_key=True,default=uid); exhibitor_id=db.Column(db.Uuid,db.ForeignKey("exhibitors.id"),nullable=False,index=True); category_id=db.Column(db.Uuid,db.ForeignKey("categories.id"),nullable=False,index=True)
    nombre=db.Column(db.String(200),nullable=False); slug=db.Column(db.String(220),nullable=False); descripcion=db.Column(db.Text,nullable=False); materiales_o_ingredientes=db.Column(db.Text); lugar_origen=db.Column(db.String(150)); presentacion=db.Column(db.String(150)); informacion_adicional=db.Column(db.Text)
    estado=db.Column(db.Enum(ProductStatus,name="product_status"),nullable=False,default=ProductStatus.AVAILABLE); destacado=db.Column(db.Boolean,default=False,nullable=False); deleted_at=db.Column(db.DateTime(timezone=True)); __table_args__=(UniqueConstraint("exhibitor_id","slug"),)

class ProductImage(db.Model):
    __tablename__="product_images"; id=db.Column(db.Uuid,primary_key=True,default=uid); product_id=db.Column(db.Uuid,db.ForeignKey("products.id",ondelete="CASCADE"),nullable=False); filename=db.Column(db.String(255),nullable=False); url=db.Column(db.String(500),nullable=False); alt_text=db.Column(db.String(255)); is_cover=db.Column(db.Boolean,default=False); display_order=db.Column(db.Integer,default=0); created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False)

class PasswordRecovery(db.Model):
    __tablename__="password_recoveries"; id=db.Column(db.Uuid,primary_key=True,default=uid); user_id=db.Column(db.Uuid,db.ForeignKey("users.id"),nullable=False,index=True); token_hash=db.Column(db.String(64),unique=True,nullable=False); expires_at=db.Column(db.DateTime(timezone=True),nullable=False); used_at=db.Column(db.DateTime(timezone=True)); created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False)

class Audit(db.Model):
    __tablename__="audits"; id=db.Column(db.Uuid,primary_key=True,default=uid); user_id=db.Column(db.Uuid,db.ForeignKey("users.id"),index=True); accion=db.Column(db.String(100),nullable=False,index=True); entidad=db.Column(db.String(100),nullable=False); entidad_id=db.Column(db.Uuid); descripcion=db.Column(db.Text); datos_anteriores=db.Column(db.JSON); datos_nuevos=db.Column(db.JSON); ip_address=db.Column(db.String(45)); user_agent=db.Column(db.String(500)); created_at=db.Column(db.DateTime(timezone=True),default=now,nullable=False,index=True)

