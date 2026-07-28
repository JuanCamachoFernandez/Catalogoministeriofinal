"""Create isolated registration requests for manual QA of the admin flow."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select

from app import create_app
from app.extensions import db
from app.models import (
    ProductiveSector,
    ProductiveUnit,
    ProductiveUnitStatus,
    RegistrationRequest,
    RegistrationRequestProduct,
    RegistrationRequestSector,
    RegistrationStatus,
    Role,
    SectorStatus,
    UnitSector,
    User,
    UserStatus,
    NotificationStatus,
)


QA_CASES = (
    ("PENDING", RegistrationStatus.PENDING, "qa.pendiente"),
    ("APPROVED", RegistrationStatus.APPROVED, "qa.aprobada"),
    ("REJECTED", RegistrationStatus.REJECTED, "qa.rechazada"),
)


def media_urls(app):
    folder = Path(app.config["CARPETA_CARGAS"]) / "solicitudes"
    files = sorted(path for path in folder.glob("*") if path.is_file())
    if len(files) < 2:
        raise RuntimeError(
            "Se necesitan al menos dos imagenes en backend/uploads/solicitudes "
            "para crear los casos QA."
        )
    return [f"/uploads/solicitudes/{path.name}" for path in files]


def get_admin():
    admin_roles = [Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO, Role.ADMIN]
    admin = db.session.scalar(
        select(User).where(User.role.in_(admin_roles), User.deleted_at.is_(None))
    )
    if not admin:
        raise RuntimeError("Debe existir un administrador para crear los casos QA.")
    return admin


def get_sector():
    sector = db.session.scalar(
        select(ProductiveSector).where(ProductiveSector.estado == SectorStatus.ACTIVE)
    )
    if sector:
        return sector
    sector = ProductiveSector(
        nombre="QA - Sector de prueba",
        estado=SectorStatus.ACTIVE,
        es_otro=False,
    )
    db.session.add(sector)
    db.session.flush()
    return sector


def ensure_three_sectors(request):
    active_sectors = db.session.scalars(
        select(ProductiveSector)
        .where(ProductiveSector.estado == SectorStatus.ACTIVE)
        .order_by(ProductiveSector.nombre)
        .limit(3)
    ).all()
    while len(active_sectors) < 3:
        sector = ProductiveSector(
            nombre=f"QA - Sector adicional {len(active_sectors) + 1}",
            estado=SectorStatus.ACTIVE,
            es_otro=False,
        )
        db.session.add(sector)
        db.session.flush()
        active_sectors.append(sector)

    selected_ids = [sector.id for sector in active_sectors]
    db.session.execute(
        delete(RegistrationRequestSector).where(
            RegistrationRequestSector.registration_request_id == request.id,
            ~RegistrationRequestSector.productive_sector_id.in_(selected_ids),
        )
    )
    linked_ids = set(db.session.scalars(
        select(RegistrationRequestSector.productive_sector_id).where(
            RegistrationRequestSector.registration_request_id == request.id
        )
    ).all())
    for sector in active_sectors:
        if sector.id not in linked_ids:
            db.session.add(RegistrationRequestSector(
                registration_request_id=request.id,
                productive_sector_id=sector.id,
            ))


def create_request(case, status, email_prefix, admin, sector, images):
    email = f"{email_prefix}@gmail.com"
    existing = db.session.scalar(
        select(RegistrationRequest).where(
            RegistrationRequest.correo_electronico == email
        )
    )
    if existing:
        if status == RegistrationStatus.PENDING:
            ensure_three_sectors(existing)
        return False

    name = f"QA Solicitud {case.title()}"
    request = RegistrationRequest(
        nombre_comercial=name,
        razon_social=f"{name} SRL",
        nit=f"98765{len(case):04d}",
        registro_seprec=f"87654{len(case):04d}",
        registro_pro_bolivia=f"76543{len(case):04d}",
        nombres_representante="Maria Fernanda",
        apellido_paterno_representante="Quispe",
        apellido_materno_representante="Mamani",
        departamento="La Paz",
        direccion_fisica="Av. QA 123, zona central",
        telefono_whatsapp="71234567",
        correo_electronico=email,
        facebook_url="https://facebook.com/qa.solicitud",
        instagram_url="https://instagram.com/qa.solicitud",
        tiktok_url="https://tiktok.com/@qa.solicitud",
        resena_comercial=(
            "Caso de prueba para revisar todos los datos de una solicitud "
            "desde el panel administrativo."
        ),
        logo_url=images[0],
        estado=status,
        reviewed_by=admin.id if status != RegistrationStatus.PENDING else None,
        fecha_revision=(
            datetime.now(timezone.utc) if status != RegistrationStatus.PENDING else None
        ),
        notification_status=(
            NotificationStatus.SENT if status != RegistrationStatus.PENDING else None
        ),
        motivo_rechazo=(
            "Caso QA rechazado: falta documentacion de respaldo para validar la solicitud."
            if status == RegistrationStatus.REJECTED
            else None
        ),
    )
    db.session.add(request)
    db.session.flush()
    db.session.add(RegistrationRequestSector(
        registration_request_id=request.id,
        productive_sector_id=sector.id,
    ))
    if status == RegistrationStatus.PENDING:
        ensure_three_sectors(request)
    for order in range(1, 4):
        db.session.add(RegistrationRequestProduct(
            registration_request_id=request.id,
            nombre_comercial=f"Producto QA {order} - {case.title()}",
            descripcion_tecnica=(
                f"Descripcion tecnica del producto QA {order}. "
                "Permite validar textos largos, precio e imagen."
            ),
            precio_referencia=Decimal(f"{order * 25}.00"),
            imagen_url=images[(order - 1) % len(images)],
            orden=order,
        ))

    if status == RegistrationStatus.APPROVED:
        create_approved_unit(request, admin, sector)
    return True


def create_approved_unit(request, admin, sector):
    user = User(
        username="qa.solicitud.aprobada",
        email=request.correo_electronico,
        role=Role.PRODUCTIVE_UNIT_RESPONSIBLE,
        first_name=request.nombres_representante,
        last_name=request.apellido_paterno_representante,
        apellido_paterno=request.apellido_paterno_representante,
        apellido_materno=request.apellido_materno_representante,
        phone=request.telefono_whatsapp,
        status=UserStatus.ACTIVE,
        must_change_password=False,
    )
    user.set_password("QA.Solicitud2026!")
    db.session.add(user)
    db.session.flush()
    unit = ProductiveUnit(
        user_id=user.id,
        registration_request_id=request.id,
        nombre_comercial=request.nombre_comercial,
        razon_social=request.razon_social,
        nit=request.nit,
        registro_seprec=request.registro_seprec,
        registro_pro_bolivia=request.registro_pro_bolivia,
        nombres_representante=request.nombres_representante,
        apellido_paterno_representante=request.apellido_paterno_representante,
        apellido_materno_representante=request.apellido_materno_representante,
        departamento=request.departamento,
        direccion_fisica=request.direccion_fisica,
        telefono_whatsapp=request.telefono_whatsapp,
        correo_electronico=request.correo_electronico,
        facebook_url=request.facebook_url,
        instagram_url=request.instagram_url,
        tiktok_url=request.tiktok_url,
        resena_comercial=request.resena_comercial,
        logo_url=request.logo_url,
        estado=ProductiveUnitStatus.ACTIVE,
        fecha_aprobacion=request.fecha_revision,
    )
    db.session.add(unit)
    db.session.flush()
    db.session.add(UnitSector(
        productive_unit_id=unit.id,
        productive_sector_id=sector.id,
        estado=SectorStatus.ACTIVE,
    ))


def main():
    app = create_app()
    with app.app_context():
        admin = get_admin()
        sector = get_sector()
        images = media_urls(app)
        created = [
            case
            for case, status, email_prefix in QA_CASES
            if create_request(case, status, email_prefix, admin, sector, images)
        ]
        db.session.commit()
        print("Casos QA creados: " + (", ".join(created) if created else "ninguno; ya existian"))
        print("Credenciales de la unidad aprobada: qa.solicitud.aprobada / QA.Solicitud2026!")


if __name__ == "__main__":
    main()
