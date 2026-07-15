from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import wraps
import os
from urllib.parse import quote
import uuid
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy import func, select
from werkzeug.utils import secure_filename
from .extensions import db
from .models import User, UserStatus, Role, AdminProfile, Audit, DocumentType, Exhibitor, ExhibitorType, ExhibitorTypeLink, Fair, FeriaStatus, FairImage, FairExhibitor, AssignmentStatus, Product, ProductStatus, ProductImage, Category
from .utils import normalize_whatsapp, slugify, temporary_password, valid_gmail

api=Blueprint("api",__name__)
def error(message,status=400): return jsonify({"error":message}),status
ALLOWED_EXTENSIONS={"png","jpg","jpeg","webp","gif"}
def user_json(u): return {"id":str(u.id),"username":u.username,"email":u.email,"role":u.role.value,"first_name":u.first_name,"last_name":u.last_name,"must_change_password":u.must_change_password}
def current_user():
    identity = get_jwt_identity()
    try:
        user_id = uuid.UUID(identity)
    except (ValueError, TypeError, AttributeError):
        return None
    return db.session.get(User, user_id)
def roles(*allowed):
    def deco(fn):
        @wraps(fn)
        @jwt_required()
        def wrapped(*args,**kwargs):
            u=current_user()
            if not u or u.status!=UserStatus.ACTIVE:return error("Cuenta no disponible",403)
            if u.must_change_password:return error("Debe cambiar su contraseña",403)
            if u.role not in allowed:return error("No autorizado",403)
            return fn(*args,**kwargs)
        return wrapped
    return deco

def audit(action, entity, entity_id=None, description=None, before=None, after=None):
    user=current_user()
    db.session.add(Audit(user_id=user.id if user else None,accion=action,entidad=entity,entidad_id=entity_id,descripcion=description,datos_anteriores=before,datos_nuevos=after,ip_address=request.remote_addr,user_agent=request.user_agent.string[:500]))

def unique_username(first_name,last_name):
    base=slugify(f"{first_name}.{last_name}").replace('-','.') or 'usuario';candidate=base;number=1
    while db.session.scalar(select(User.id).where(User.username==candidate)):
        candidate=f"{base}{number:02d}";number+=1
    return candidate

def admin_user_json(user):
    profile=user.admin_profile
    return {**user_json(user),"phone":user.phone,"status":user.status.value,"cargo":profile.cargo if profile else None,"unidad":profile.unidad if profile else None,"created_at":user.created_at.isoformat()}

def parse_money(value):
    if value in (None,""): return None
    try:
        amount=Decimal(str(value))
    except (InvalidOperation,ValueError):
        raise ValueError("El precio debe ser numérico")
    if amount<0: raise ValueError("El precio no puede ser negativo")
    return amount.quantize(Decimal("0.01"))

def active_fair_query():
    return select(Fair).where(Fair.estado==FeriaStatus.PUBLISHED,Fair.visible_publicamente.is_(True),Fair.deleted_at.is_(None))

def ensure_unique_active_fair(fair):
    for other in db.session.scalars(active_fair_query().where(Fair.id!=fair.id)).all():
        other.estado=FeriaStatus.DISABLED;other.visible_publicamente=False

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file, folder):
    if not file or not file.filename:return None
    if not allowed_file(file.filename):raise ValueError("Formato de imagen no permitido")
    ext=file.filename.rsplit(".",1)[1].lower();name=f"{uuid.uuid4().hex}.{ext}"
    relative=os.path.join(folder,name).replace("\\","/")
    target=os.path.join(current_app.config["UPLOAD_FOLDER"],folder)
    os.makedirs(target,exist_ok=True)
    file.save(os.path.join(target,secure_filename(name)))
    return f"/uploads/{relative}"

@api.post("/auth/login")
def login():
    d=request.get_json() or {}; value=(d.get("login") or "").lower().strip()
    u=db.session.scalar(select(User).where((User.email==value)|(User.username==value)))
    if not u or not u.check_password(d.get("password","")) or u.status!=UserStatus.ACTIVE:
        if u:u.failed_login_attempts+=1;db.session.commit()
        return error("Credenciales inválidas",401)
    u.failed_login_attempts=0;u.last_login_at=datetime.now(timezone.utc);db.session.commit()
    return {"access_token":create_access_token(identity=str(u.id)),"user":user_json(u)}

@api.get("/auth/me")
@jwt_required()
def me():
    u=current_user();return user_json(u) if u else error("No autorizado",401)

@api.post("/auth/change-password")
@jwt_required()
def change_password():
    u=current_user();d=request.get_json() or {};new=d.get("new_password","")
    if not u or not u.check_password(d.get("current_password","")):return error("La contraseña actual no es correcta")
    if len(new)<10 or not all((any(c.isupper() for c in new),any(c.islower() for c in new),any(c.isdigit() for c in new),any(not c.isalnum() for c in new))):return error("La contraseña no cumple los requisitos")
    if u.check_password(new):return error("No puede reutilizar la contraseña")
    u.set_password(new);u.must_change_password=False;u.password_changed_at=datetime.now(timezone.utc);db.session.commit();return {"message":"Contraseña actualizada"}

@api.post("/uploads")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO,Role.EXPOSITOR)
def upload_file():
    folder=request.form.get("folder","general")
    if folder not in ("general","ferias","productos","logos"):folder="general"
    try:url=save_upload(request.files.get("file"),folder)
    except ValueError as exc:return error(str(exc))
    if not url:return error("Debe enviar un archivo")
    return {"url":url},201

def fair_json(f):return {"id":str(f.id),"nombre":f.nombre,"slug":f.slug,"descripcion":f.descripcion,"lugar":f.lugar,"direccion":f.direccion,"departamento":f.departamento,"municipio":f.municipio,"fecha_inicio":f.fecha_inicio.isoformat(),"fecha_fin":f.fecha_fin.isoformat(),"hora_inicio":f.hora_inicio.isoformat() if f.hora_inicio else None,"hora_fin":f.hora_fin.isoformat() if f.hora_fin else None,"fecha_limite_registro":f.fecha_limite_registro.isoformat() if f.fecha_limite_registro else None,"imagen_portada":f.imagen_portada,"observaciones":f.observaciones,"visible_publicamente":f.visible_publicamente,"estado":f.estado.value}
def product_json(p):
    imgs=db.session.scalars(select(ProductImage).where(ProductImage.product_id==p.id).order_by(ProductImage.is_cover.desc(),ProductImage.display_order)).all()
    return {"id":str(p.id),"exhibitor_id":str(p.exhibitor_id),"category_id":str(p.category_id),"nombre":p.nombre,"slug":p.slug,"descripcion":p.descripcion,"materiales_o_ingredientes":p.materiales_o_ingredientes,"lugar_origen":p.lugar_origen,"presentacion":p.presentacion,"informacion_adicional":p.informacion_adicional,"precio":float(p.precio) if p.precio is not None else None,"estado":p.estado.value,"destacado":p.destacado,"imagenes":[{"id":str(i.id),"url":i.url,"is_cover":i.is_cover,"display_order":i.display_order} for i in imgs]}

def product_from_payload(product,d,exhibitor_id=None):
    if exhibitor_id:product.exhibitor_id=exhibitor_id
    if "category_id" in d:
        try:product.category_id=uuid.UUID(d.get("category_id",""))
        except (ValueError,TypeError):raise ValueError("Categoría inválida")
    if "nombre" in d:
        name=(d.get("nombre") or "").strip()
        if not name:raise ValueError("El nombre del producto es obligatorio")
        product.nombre=name;product.slug=slugify(name)
    if "descripcion" in d: product.descripcion=d.get("descripcion") or ""
    if "precio" in d: product.precio=parse_money(d.get("precio"))
    for field in ("materiales_o_ingredientes","lugar_origen","presentacion","informacion_adicional"):
        if field in d:setattr(product,field,d.get(field))
    if "estado" in d: product.estado=ProductStatus(d.get("estado"))
    if "destacado" in d: product.destacado=bool(d.get("destacado"))
    return product

@api.get("/public/fairs")
def public_fairs():
    q=select(Fair).where(Fair.estado==FeriaStatus.PUBLISHED,Fair.visible_publicamente.is_(True),Fair.deleted_at.is_(None));term=request.args.get("q");dept=request.args.get("departamento")
    if term:q=q.where(Fair.nombre.ilike(f"%{term}%"))
    if dept:q=q.where(Fair.departamento==dept)
    return {"items":[fair_json(x) for x in db.session.scalars(q.order_by(Fair.fecha_inicio.desc())).all()]}

@api.get("/public/active-fair")
def public_active_fair():
    f=db.session.scalar(active_fair_query().order_by(Fair.fecha_inicio.desc()))
    if not f:return error("No existe una feria activa",404)
    rows=db.session.execute(select(Exhibitor,FairExhibitor).join(FairExhibitor,FairExhibitor.exhibitor_id==Exhibitor.id).where(FairExhibitor.fair_id==f.id,FairExhibitor.estado==AssignmentStatus.AUTHORIZED,Exhibitor.estado==UserStatus.ACTIVE,Exhibitor.deleted_at.is_(None))).all()
    return {**fair_json(f),"expositores":[{"id":str(e.id),"nombre_comercial":e.nombre_comercial,"descripcion":e.descripcion,"logo":e.logo,"numero_stand":a.numero_stand,"sector":a.sector} for e,a in rows]}

@api.get("/public/fairs/<slug>")
def public_fair(slug):
    f=db.session.scalar(select(Fair).where(Fair.slug==slug,Fair.estado==FeriaStatus.PUBLISHED,Fair.visible_publicamente.is_(True),Fair.deleted_at.is_(None)))
    if not f:return error("Feria no encontrada",404)
    rows=db.session.execute(select(Exhibitor,FairExhibitor).join(FairExhibitor,FairExhibitor.exhibitor_id==Exhibitor.id).where(FairExhibitor.fair_id==f.id,FairExhibitor.estado==AssignmentStatus.AUTHORIZED,Exhibitor.estado==UserStatus.ACTIVE,Exhibitor.deleted_at.is_(None))).all()
    return {**fair_json(f),"expositores":[{"id":str(e.id),"nombre_comercial":e.nombre_comercial,"descripcion":e.descripcion,"logo":e.logo,"numero_stand":a.numero_stand,"sector":a.sector} for e,a in rows]}

@api.get("/public/fairs/<slug>/exhibitors/<uuid:exhibitor_id>")
def public_exhibitor(slug,exhibitor_id):
    row=db.session.execute(select(Fair,Exhibitor).join(FairExhibitor,FairExhibitor.fair_id==Fair.id).join(Exhibitor,Exhibitor.id==FairExhibitor.exhibitor_id).where(Fair.slug==slug,Fair.estado==FeriaStatus.PUBLISHED,Fair.visible_publicamente.is_(True),FairExhibitor.exhibitor_id==exhibitor_id,FairExhibitor.estado==AssignmentStatus.AUTHORIZED,Exhibitor.estado==UserStatus.ACTIVE)).first()
    if not row:return error("Expositor no disponible en esta feria",404)
    _,e=row;products=db.session.scalars(select(Product).where(Product.exhibitor_id==e.id,Product.estado.in_([ProductStatus.AVAILABLE,ProductStatus.OUT_OF_STOCK]),Product.deleted_at.is_(None))).all()
    return {"id":str(e.id),"nombre_comercial":e.nombre_comercial,"descripcion":e.descripcion,"productos":[product_json(p) for p in products]}

@api.post("/public/whatsapp-query")
def whatsapp_query():
    """El servidor deriva el destinatario del propietario; nunca acepta un teléfono del cliente."""
    d=request.get_json() or {};ids=d.get("product_ids") or []
    if not ids:return error("Seleccione al menos un producto")
    try:product_ids=[uuid.UUID(x) for x in ids]
    except (ValueError,TypeError):return error("Productos inválidos")
    products=db.session.scalars(select(Product).where(Product.id.in_(product_ids),Product.estado==ProductStatus.AVAILABLE,Product.deleted_at.is_(None))).all()
    if len(products)!=len(set(product_ids)):return error("Algún producto no está disponible")
    owners={p.exhibitor_id for p in products}
    if len(owners)!=1:return error("La consulta solo puede contener productos de un mismo expositor")
    owner_id=owners.pop();exhibitor=db.session.get(Exhibitor,owner_id)
    assignment=db.session.scalar(select(FairExhibitor).join(Fair).where(Fair.slug==d.get("fair_slug"),Fair.estado==FeriaStatus.PUBLISHED,Fair.visible_publicamente.is_(True),FairExhibitor.exhibitor_id==owner_id,FairExhibitor.estado==AssignmentStatus.AUTHORIZED))
    if not assignment or not exhibitor or exhibitor.estado!=UserStatus.ACTIVE:return error("El expositor no está autorizado en esta feria",403)
    phone=normalize_whatsapp(exhibitor.telefono_whatsapp);names="\n".join(f"• {p.nombre}" for p in products);message=f"Hola, vi sus productos en el Catálogo Digital de Ferias y quisiera consultar por:\n{names}\n\nExpositor: {exhibitor.nombre_comercial}"
    return {"url":f"https://wa.me/{phone}?text={quote(message)}"}

@api.get("/exhibitor/products")
@roles(Role.EXPOSITOR)
def own_products():
    e=current_user().exhibitor;return {"items":[product_json(p) for p in db.session.scalars(select(Product).where(Product.exhibitor_id==e.id,Product.deleted_at.is_(None))).all()]}

@api.post("/exhibitor/products")
@roles(Role.EXPOSITOR)
def create_product():
    e=current_user().exhibitor;d=request.get_json() or {}
    try:p=product_from_payload(Product(estado=ProductStatus.AVAILABLE),d,e.id)
    except ValueError as exc:return error(str(exc))
    if not p.category_id or not p.descripcion:return error("Categoría y descripción son obligatorias")
    db.session.add(p);audit("CREAR","Producto",p.id,"Producto creado por expositor");db.session.commit();return product_json(p),201

@api.patch("/exhibitor/products/<uuid:product_id>")
@roles(Role.EXPOSITOR)
def update_own_product(product_id):
    e=current_user().exhibitor;p=db.session.get(Product,product_id)
    if not p or p.exhibitor_id!=e.id or p.deleted_at:return error("Producto no encontrado",404)
    try:product_from_payload(p,request.get_json() or {})
    except ValueError as exc:return error(str(exc))
    audit("EDITAR","Producto",p.id,"Producto actualizado por expositor");db.session.commit();return product_json(p)

@api.post("/exhibitor/products/<uuid:product_id>/images")
@roles(Role.EXPOSITOR)
def add_own_product_image(product_id):
    e=current_user().exhibitor;p=db.session.get(Product,product_id)
    if not p or p.exhibitor_id!=e.id or p.deleted_at:return error("Producto no encontrado",404)
    return add_product_image(p)

@api.get("/categories")
@jwt_required()
def categories():return {"items":[{"id":str(c.id),"nombre":c.nombre} for c in db.session.scalars(select(Category).where(Category.estado.is_(True),Category.deleted_at.is_(None))).all()]}

@api.get("/admin/dashboard")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def admin_dashboard():
    count=lambda model,*conditions:db.session.scalar(select(func.count()).select_from(model).where(*conditions)) or 0
    active=db.session.scalar(active_fair_query().order_by(Fair.fecha_inicio.desc()))
    return {"stats":{"ferias":count(Fair,Fair.deleted_at.is_(None)),"feria_activa":active.nombre if active else None,"ferias_publicadas":count(Fair,Fair.estado==FeriaStatus.PUBLISHED,Fair.deleted_at.is_(None)),"expositores":count(Exhibitor,Exhibitor.deleted_at.is_(None)),"expositores_activos":count(Exhibitor,Exhibitor.estado==UserStatus.ACTIVE,Exhibitor.deleted_at.is_(None)),"productos":count(Product,Product.deleted_at.is_(None)),"productos_disponibles":count(Product,Product.estado==ProductStatus.AVAILABLE,Product.deleted_at.is_(None)),"productos_sin_stock":count(Product,Product.estado==ProductStatus.OUT_OF_STOCK,Product.deleted_at.is_(None)),"asignaciones_pendientes":count(FairExhibitor,FairExhibitor.estado==AssignmentStatus.PENDING)},"recent_audits":[{"id":str(a.id),"accion":a.accion,"entidad":a.entidad,"descripcion":a.descripcion,"created_at":a.created_at.isoformat()} for a in db.session.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(8)).all()]}

@api.get("/admin/users")
@roles(Role.SUPERADMIN)
def list_admin_users():
    q=select(User).where(User.role.in_([Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO]),User.deleted_at.is_(None));term=request.args.get("q","").strip()
    if term:q=q.where((User.first_name.ilike(f"%{term}%"))|(User.last_name.ilike(f"%{term}%"))|(User.email.ilike(f"%{term}%")))
    return {"items":[admin_user_json(u) for u in db.session.scalars(q.order_by(User.created_at.desc())).all()]}

@api.post("/admin/users")
@roles(Role.SUPERADMIN)
def create_admin_user():
    d=request.get_json() or {};email=(d.get("email") or "").lower().strip();role=Role(d.get("role","ADMIN_VICEMINISTERIO"))
    if role not in (Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO):return error("Rol administrativo inválido")
    if not valid_gmail(email):return error("El correo debe ser una dirección @gmail.com válida")
    if db.session.scalar(select(User.id).where(User.email==email)):return error("El Gmail ya está registrado",409)
    if not d.get("first_name") or not d.get("last_name"):return error("Nombres y apellidos son obligatorios")
    password=temporary_password();user=User(username=unique_username(d["first_name"],d["last_name"]),email=email,role=role,first_name=d["first_name"].strip(),last_name=d["last_name"].strip(),phone=d.get("phone"),status=UserStatus.ACTIVE,must_change_password=True);user.set_password(password);db.session.add(user);db.session.flush();db.session.add(AdminProfile(user_id=user.id,cargo=d.get("cargo"),unidad=d.get("unidad"),observaciones=d.get("observaciones")));audit("CREAR","Usuario",user.id,"Administrador creado",after={"email":email,"role":role.value});db.session.commit()
    return {"message":"Administrador creado","data":admin_user_json(user),"temporary_password":password},201

@api.patch("/admin/users/<uuid:user_id>/status")
@roles(Role.SUPERADMIN)
def change_admin_status(user_id):
    target=db.session.get(User,user_id);actor=current_user();d=request.get_json() or {}
    if not target or target.role not in (Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO):return error("Administrador no encontrado",404)
    new_status=UserStatus(d.get("status"))
    if target.id==actor.id and new_status!=UserStatus.ACTIVE:return error("No puede inhabilitar su propia cuenta")
    if target.role==Role.SUPERADMIN and new_status!=UserStatus.ACTIVE:
        active=db.session.scalar(select(func.count()).select_from(User).where(User.role==Role.SUPERADMIN,User.status==UserStatus.ACTIVE,User.deleted_at.is_(None)))
        if active<=1:return error("No puede inhabilitar al último SUPERADMIN activo")
    old=target.status.value;target.status=new_status;audit("CAMBIAR_ESTADO","Usuario",target.id,f"Estado {old} → {new_status.value}");db.session.commit();return {"message":"Estado actualizado","data":admin_user_json(target)}

@api.get("/fairs")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def list_fairs():
    q=select(Fair).where(Fair.deleted_at.is_(None));term=request.args.get("q","").strip();state=request.args.get("estado")
    if term:q=q.where(Fair.nombre.ilike(f"%{term}%"))
    if state:q=q.where(Fair.estado==FeriaStatus(state))
    return {"items":[fair_json(f) for f in db.session.scalars(q.order_by(Fair.fecha_inicio.desc())).all()]}

@api.post("/fairs")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def create_fair():
    d=request.get_json() or {}
    try:start=date.fromisoformat(d.get("fecha_inicio",""));end=date.fromisoformat(d.get("fecha_fin",""))
    except ValueError:return error("Las fechas son obligatorias y deben ser válidas")
    if end<start:return error("La fecha final no puede ser anterior a la inicial")
    required=(d.get("nombre"),d.get("lugar"),d.get("departamento"),d.get("municipio"),d.get("imagen_portada"))
    if not all(required):return error("Nombre, ubicación e imagen de portada son obligatorios")
    base=slugify(d["nombre"]);slug=base;number=1
    while db.session.scalar(select(Fair.id).where(Fair.slug==slug)):slug=f"{base}-{number}";number+=1
    fair=Fair(nombre=d["nombre"].strip(),slug=slug,descripcion=d.get("descripcion"),lugar=d["lugar"].strip(),direccion=d.get("direccion"),departamento=d["departamento"],municipio=d["municipio"],fecha_inicio=start,fecha_fin=end,imagen_portada=d["imagen_portada"],observaciones=d.get("observaciones"),estado=FeriaStatus.DRAFT,visible_publicamente=False,created_by=current_user().id);db.session.add(fair);db.session.flush();audit("CREAR","Feria",fair.id,"Feria creada");db.session.commit();return fair_json(fair),201

@api.patch("/fairs/<uuid:fair_id>/status")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def change_fair_status(fair_id):
    fair=db.session.get(Fair,fair_id)
    if not fair or fair.deleted_at:return error("Feria no encontrada",404)
    status=FeriaStatus((request.get_json() or {}).get("status"));fair.estado=status;fair.visible_publicamente=status==FeriaStatus.PUBLISHED
    if status==FeriaStatus.PUBLISHED:ensure_unique_active_fair(fair)
    audit("CAMBIAR_ESTADO","Feria",fair.id,f"Estado cambiado a {status.value}");db.session.commit();return fair_json(fair)

@api.patch("/fairs/<uuid:fair_id>")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def update_fair(fair_id):
    fair=db.session.get(Fair,fair_id);d=request.get_json() or {}
    if not fair or fair.deleted_at:return error("Feria no encontrada",404)
    if "fecha_inicio" in d or "fecha_fin" in d:
        try:
            start=date.fromisoformat(d.get("fecha_inicio") or fair.fecha_inicio.isoformat())
            end=date.fromisoformat(d.get("fecha_fin") or fair.fecha_fin.isoformat())
        except ValueError:return error("Las fechas deben ser válidas")
        if end<start:return error("La fecha final no puede ser anterior a la inicial")
        fair.fecha_inicio=start;fair.fecha_fin=end
    for field in ("nombre","descripcion","lugar","direccion","departamento","municipio","imagen_portada","observaciones"):
        if field in d:setattr(fair,field,d.get(field))
    if "nombre" in d:
        base=slugify(fair.nombre);slug=base;number=1
        while db.session.scalar(select(Fair.id).where(Fair.slug==slug,Fair.id!=fair.id)):
            slug=f"{base}-{number}";number+=1
        fair.slug=slug
    audit("EDITAR","Feria",fair.id,"Feria actualizada");db.session.commit();return fair_json(fair)

@api.post("/fairs/<uuid:fair_id>/images")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def add_fair_image(fair_id):
    fair=db.session.get(Fair,fair_id)
    if not fair or fair.deleted_at:return error("Feria no encontrada",404)
    try:url=save_upload(request.files.get("file"),"ferias")
    except ValueError as exc:return error(str(exc))
    if not url:url=(request.get_json(silent=True) or {}).get("url")
    if not url:return error("Debe enviar una imagen")
    img=FairImage(fair_id=fair.id,filename=os.path.basename(url),url=url,alt_text=request.form.get("alt_text"),is_cover=False)
    db.session.add(img);audit("AGREGAR_IMAGEN","Feria",fair.id,"Imagen agregada");db.session.commit();return {"id":str(img.id),"url":img.url},201

def assignment_json(a):
    e=db.session.get(Exhibitor,a.exhibitor_id)
    return {"id":str(a.id),"fair_id":str(a.fair_id),"exhibitor_id":str(a.exhibitor_id),"nombre_comercial":e.nombre_comercial if e else None,"estado":a.estado.value,"numero_stand":a.numero_stand,"sector":a.sector,"observaciones":a.observaciones,"authorized_by":str(a.authorized_by) if a.authorized_by else None,"authorized_at":a.authorized_at.isoformat() if a.authorized_at else None}

@api.get("/fairs/<uuid:fair_id>/exhibitors")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def fair_assignments(fair_id):
    if not db.session.get(Fair,fair_id):return error("Feria no encontrada",404)
    q=select(FairExhibitor).where(FairExhibitor.fair_id==fair_id).order_by(FairExhibitor.created_at.desc())
    return {"items":[assignment_json(a) for a in db.session.scalars(q).all()]}

@api.post("/fairs/<uuid:fair_id>/exhibitors")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def assign_exhibitor(fair_id):
    fair=db.session.get(Fair,fair_id);d=request.get_json() or {}
    if not fair or fair.deleted_at:return error("Feria no encontrada",404)
    try:exhibitor_id=uuid.UUID(d.get("exhibitor_id",""))
    except (ValueError,TypeError):return error("Expositor inválido")
    exhibitor=db.session.get(Exhibitor,exhibitor_id)
    if not exhibitor or exhibitor.deleted_at:return error("Expositor no encontrado",404)
    existing=db.session.scalar(select(FairExhibitor).where(FairExhibitor.fair_id==fair_id,FairExhibitor.exhibitor_id==exhibitor_id))
    if existing:return error("El expositor ya está asignado a la feria",409)
    status=AssignmentStatus(d.get("estado","AUTHORIZED"))
    a=FairExhibitor(fair_id=fair_id,exhibitor_id=exhibitor_id,estado=status,numero_stand=d.get("numero_stand"),sector=d.get("sector"),observaciones=d.get("observaciones"))
    if status==AssignmentStatus.AUTHORIZED:a.authorized_by=current_user().id;a.authorized_at=datetime.now(timezone.utc)
    db.session.add(a);audit("ASIGNAR","FeriaExpositor",a.id,"Expositor asignado a feria");db.session.commit();return assignment_json(a),201

@api.patch("/fair-exhibitors/<uuid:assignment_id>")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def update_assignment(assignment_id):
    a=db.session.get(FairExhibitor,assignment_id);d=request.get_json() or {}
    if not a:return error("Asignación no encontrada",404)
    if "estado" in d:
        status=AssignmentStatus(d.get("estado"));a.estado=status
        if status==AssignmentStatus.AUTHORIZED:a.authorized_by=current_user().id;a.authorized_at=datetime.now(timezone.utc)
    for field in ("numero_stand","sector","observaciones"):
        if field in d:setattr(a,field,d.get(field))
    audit("EDITAR","FeriaExpositor",a.id,"Asignación actualizada");db.session.commit();return assignment_json(a)

@api.get("/admin/categories")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def admin_categories():return {"items":[{"id":str(c.id),"nombre":c.nombre,"slug":c.slug,"descripcion":c.descripcion,"estado":c.estado} for c in db.session.scalars(select(Category).where(Category.deleted_at.is_(None)).order_by(Category.nombre)).all()]}

@api.post("/categories")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def create_category():
    d=request.get_json() or {};name=(d.get("nombre") or "").strip()
    if not name:return error("El nombre es obligatorio")
    if db.session.scalar(select(Category.id).where(func.lower(Category.nombre)==name.lower(),Category.deleted_at.is_(None))):return error("La categoría ya existe",409)
    category=Category(nombre=name,slug=slugify(name),descripcion=d.get("descripcion"),estado=True);db.session.add(category);db.session.flush();audit("CREAR","Categoria",category.id,"Categoría creada");db.session.commit();return {"id":str(category.id),"nombre":category.nombre,"estado":category.estado},201

@api.patch("/categories/<uuid:category_id>/status")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def category_status(category_id):
    category=db.session.get(Category,category_id)
    if not category or category.deleted_at:return error("Categoría no encontrada",404)
    category.estado=bool((request.get_json() or {}).get("active"));audit("CAMBIAR_ESTADO","Categoria",category.id);db.session.commit();return {"id":str(category.id),"estado":category.estado}

@api.get("/audit")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def list_audit():
    return {"items":[{"id":str(a.id),"accion":a.accion,"entidad":a.entidad,"entidad_id":str(a.entidad_id) if a.entidad_id else None,"descripcion":a.descripcion,"created_at":a.created_at.isoformat()} for a in db.session.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(200)).all()]}

def exhibitor_json(e):return {"id":str(e.id),"user_id":str(e.user_id),"nombre_comercial":e.nombre_comercial,"tipo_documento":e.tipo_documento.value,"numero_documento":e.numero_documento,"nombre_responsable":e.nombre_responsable,"apellido_responsable":e.apellido_responsable,"telefono_whatsapp":e.telefono_whatsapp,"correo":e.correo,"departamento":e.departamento,"municipio":e.municipio,"direccion":e.direccion,"descripcion":e.descripcion,"descripcion_productos":e.descripcion_productos,"logo":e.logo,"estado":e.estado.value,"created_at":e.created_at.isoformat()}

@api.get("/exhibitor-types")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def exhibitor_types():return {"items":[{"id":str(t.id),"nombre":t.nombre} for t in db.session.scalars(select(ExhibitorType).where(ExhibitorType.estado.is_(True)).order_by(ExhibitorType.nombre)).all()]}

@api.get("/exhibitors")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def list_exhibitors():
    q=select(Exhibitor).where(Exhibitor.deleted_at.is_(None));term=request.args.get("q","").strip();department=request.args.get("departamento");state=request.args.get("estado")
    if term:q=q.where((Exhibitor.nombre_comercial.ilike(f"%{term}%"))|(Exhibitor.correo.ilike(f"%{term}%"))|(Exhibitor.numero_documento.ilike(f"%{term}%")))
    if department:q=q.where(Exhibitor.departamento==department)
    if state:q=q.where(Exhibitor.estado==UserStatus(state))
    return {"items":[exhibitor_json(e) for e in db.session.scalars(q.order_by(Exhibitor.created_at.desc())).all()]}

@api.post("/exhibitors")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def create_exhibitor():
    d=request.get_json() or {};email=(d.get("correo") or "").lower().strip();type_ids=d.get("type_ids") or []
    if not valid_gmail(email):return error("El correo debe ser una dirección @gmail.com válida")
    if not type_ids:return error("Seleccione al menos un tipo de expositor")
    if db.session.scalar(select(User.id).where(User.email==email)) or db.session.scalar(select(Exhibitor.id).where(Exhibitor.correo==email)):return error("El Gmail ya está registrado",409)
    if db.session.scalar(select(Exhibitor.id).where(Exhibitor.numero_documento==d.get("numero_documento"))):return error("El documento ya está registrado",409)
    try:phone=normalize_whatsapp(d.get("telefono_whatsapp"));doc_type=DocumentType(d.get("tipo_documento","CI"))
    except ValueError as exc:return error(str(exc))
    required=[d.get(x) for x in ("nombre_comercial","numero_documento","nombre_responsable","apellido_responsable","departamento","municipio")]
    if not all(required):return error("Complete todos los campos obligatorios")
    password=temporary_password();user=User(username=unique_username(d["nombre_responsable"],d["apellido_responsable"]),email=email,role=Role.EXPOSITOR,first_name=d["nombre_responsable"],last_name=d["apellido_responsable"],phone=phone,status=UserStatus.ACTIVE,must_change_password=True);user.set_password(password);db.session.add(user);db.session.flush();e=Exhibitor(user_id=user.id,nombre_comercial=d["nombre_comercial"],tipo_documento=doc_type,numero_documento=d["numero_documento"],nombre_responsable=d["nombre_responsable"],apellido_responsable=d["apellido_responsable"],telefono_whatsapp=phone,correo=email,departamento=d["departamento"],municipio=d["municipio"],direccion=d.get("direccion"),descripcion=d.get("descripcion"),descripcion_productos=d.get("descripcion_productos"),logo=d.get("logo"),estado=UserStatus.ACTIVE);db.session.add(e);db.session.flush()
    for type_id in type_ids:
        try:tid=uuid.UUID(type_id)
        except ValueError:return error("Tipo de expositor inválido")
        if not db.session.get(ExhibitorType,tid):return error("Tipo de expositor inexistente")
        db.session.add(ExhibitorTypeLink(exhibitor_id=e.id,type_id=tid))
    audit("CREAR","Expositor",e.id,"Expositor y cuenta creados");db.session.commit();return {"message":"Expositor creado","data":exhibitor_json(e),"username":user.username,"temporary_password":password},201

@api.patch("/exhibitors/<uuid:exhibitor_id>/status")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def exhibitor_status(exhibitor_id):
    e=db.session.get(Exhibitor,exhibitor_id)
    if not e or e.deleted_at:return error("Expositor no encontrado",404)
    status=UserStatus((request.get_json() or {}).get("status"));e.estado=status;e.user.status=status;audit("CAMBIAR_ESTADO","Expositor",e.id);db.session.commit();return exhibitor_json(e)

@api.patch("/exhibitors/<uuid:exhibitor_id>")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def update_exhibitor(exhibitor_id):
    e=db.session.get(Exhibitor,exhibitor_id);d=request.get_json() or {}
    if not e or e.deleted_at:return error("Expositor no encontrado",404)
    if "correo" in d:
        email=(d.get("correo") or "").lower().strip()
        if not valid_gmail(email):return error("El correo debe ser una dirección @gmail.com válida")
        if db.session.scalar(select(Exhibitor.id).where(Exhibitor.correo==email,Exhibitor.id!=e.id)):return error("El Gmail ya está registrado",409)
        e.correo=email;e.user.email=email
    if "telefono_whatsapp" in d:
        try:e.telefono_whatsapp=normalize_whatsapp(d.get("telefono_whatsapp"));e.user.phone=e.telefono_whatsapp
        except ValueError as exc:return error(str(exc))
    if "tipo_documento" in d:e.tipo_documento=DocumentType(d.get("tipo_documento"))
    for field in ("nombre_comercial","numero_documento","nombre_responsable","apellido_responsable","departamento","municipio","direccion","descripcion","descripcion_productos","logo"):
        if field in d:setattr(e,field,d.get(field))
    audit("EDITAR","Expositor",e.id,"Expositor actualizado");db.session.commit();return exhibitor_json(e)

@api.get("/products")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def list_products():
    q=select(Product).where(Product.deleted_at.is_(None));exhibitor_id=request.args.get("exhibitor_id");term=request.args.get("q","").strip()
    if exhibitor_id:q=q.where(Product.exhibitor_id==uuid.UUID(exhibitor_id))
    if term:q=q.where(Product.nombre.ilike(f"%{term}%"))
    return {"items":[product_json(p) for p in db.session.scalars(q.order_by(Product.created_at.desc())).all()]}

@api.post("/products")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def create_admin_product():
    d=request.get_json() or {}
    try:
        exhibitor_id=uuid.UUID(d.get("exhibitor_id",""))
        p=product_from_payload(Product(estado=ProductStatus.AVAILABLE),d,exhibitor_id)
    except (ValueError,TypeError) as exc:return error(str(exc) or "Datos inválidos")
    if not db.session.get(Exhibitor,exhibitor_id):return error("Expositor no encontrado",404)
    if not p.category_id or not p.descripcion:return error("Categoría y descripción son obligatorias")
    db.session.add(p);audit("CREAR","Producto",p.id,"Producto creado por administración");db.session.commit();return product_json(p),201

@api.patch("/products/<uuid:product_id>")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def update_admin_product(product_id):
    p=db.session.get(Product,product_id)
    if not p or p.deleted_at:return error("Producto no encontrado",404)
    try:product_from_payload(p,request.get_json() or {})
    except ValueError as exc:return error(str(exc))
    audit("EDITAR","Producto",p.id,"Producto actualizado por administración");db.session.commit();return product_json(p)

def add_product_image(p):
    try:url=save_upload(request.files.get("file"),"productos")
    except ValueError as exc:return error(str(exc))
    payload=request.get_json(silent=True) or {}
    if not url:url=payload.get("url")
    if not url:return error("Debe enviar una imagen")
    img=ProductImage(product_id=p.id,filename=os.path.basename(url),url=url,alt_text=request.form.get("alt_text") or payload.get("alt_text"),is_cover=bool(request.form.get("is_cover") or payload.get("is_cover")),display_order=int(request.form.get("display_order") or payload.get("display_order") or 0))
    if img.is_cover:
        for other in db.session.scalars(select(ProductImage).where(ProductImage.product_id==p.id)).all():other.is_cover=False
    db.session.add(img);audit("AGREGAR_IMAGEN","Producto",p.id,"Imagen agregada");db.session.commit();return {"id":str(img.id),"url":img.url,"is_cover":img.is_cover},201

@api.post("/products/<uuid:product_id>/images")
@roles(Role.SUPERADMIN,Role.ADMIN_VICEMINISTERIO)
def add_admin_product_image(product_id):
    p=db.session.get(Product,product_id)
    if not p or p.deleted_at:return error("Producto no encontrado",404)
    return add_product_image(p)
