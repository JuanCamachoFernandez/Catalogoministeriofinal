"""Crea datos locales idempotentes para probar el portal público."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app import create_app
from app.servicios import invalidate_public_cache
from app.extensiones import db
from app.modelos import (
    AssignmentStatus,
    Fair,
    FairParticipation,
    FeriaStatus,
    Product,
    ProductImage,
    ProductStatus,
    ProductiveSector,
    ProductiveUnit,
    ProductiveUnitStatus,
    RegistrationRequest,
    RegistrationRequestSector,
    RegistrationStatus,
    Role,
    SectorStatus,
    UnitSector,
    User,
    UserStatus,
    bolivia_today,
)
from app.modelos.usuario import ph
from app.utilidades import slugify


FAIR_DATA = (
    (
        "Feria Productiva del Altiplano",
        "Plaza Villarroel, pabellón productivo",
        "La Paz",
        "La Paz",
        "Producción, identidad y emprendimiento boliviano.",
    ),
    (
        "Encuentro Nacional de Emprendedores",
        "Campo Ferial Alalay",
        "Cochabamba",
        "Cochabamba",
        "Productos nacionales y contacto directo con sus productores.",
    ),
)

UNIT_DATA = (
    ("Sabores del Valle", "Alimentos y Bebidas Procesados", "Cochabamba"),
    ("Tejidos Jach'a", "Textiles y Confecciones", "La Paz"),
    ("Madera Viva Bolivia", "Madera y Carpintería", "Santa Cruz"),
    ("Manos de Tarija", "Artesanía Tradicional o Decorativa", "Tarija"),
    ("Belleza Natural Andina", "Cosmética Natural y Cuidado Personal", "Oruro"),
    ("Cuero Chapaco", "Cuero y Calzados", "Tarija"),
    ("Joyas del Salar", "Orfebrería y Joyería", "Potosí"),
    ("Dulces de Sucre", "Alimentos y Bebidas Procesados", "Chuquisaca"),
    ("Arte Amazónico", "Artesanía Tradicional o Decorativa", "Beni"),
)


def media_urls(upload_root: Path, folder: str) -> list[str]:
    target = upload_root / folder
    if not target.is_dir():
        return []
    return [f"/uploads/{folder}/{path.name}" for path in sorted(target.iterdir()) if path.is_file()]


def ensure_sector(name: str) -> ProductiveSector:
    sector = db.session.scalar(select(ProductiveSector).where(ProductiveSector.nombre == name))
    if sector:
        return sector
    sector = ProductiveSector(nombre=name, estado=SectorStatus.ACTIVE, es_otro=False)
    db.session.add(sector)
    db.session.flush()
    return sector


def create_demo_unit(index: int, data, admin: User, logo_urls: list[str], password_hash: str):
    name, sector_name, department = data
    email = f"expositor.demo{index:02d}@gmail.com"
    existing = db.session.scalar(select(ProductiveUnit).where(ProductiveUnit.correo_electronico == email))
    if existing:
        return existing

    user = db.session.scalar(select(User).where(User.email == email))
    if not user:
        user = User(
            username=f"expositor.demo{index:02d}",
            email=email,
            password_hash=password_hash,
            role=Role.PRODUCTIVE_UNIT_RESPONSIBLE,
            first_name="Expositor",
            last_name=f"Demostración {index}",
            apellido_paterno="Demostración",
            apellido_materno="",
            phone=f"70000{index:03d}",
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        db.session.add(user)
        db.session.flush()

    logo_url = logo_urls[(index - 1) % len(logo_urls)] if logo_urls else None
    registration = RegistrationRequest(
        nombre_comercial=name,
        razon_social=f"{name} SRL",
        nit=f"90000{index:04d}",
        registro_seprec=f"80000{index:04d}",
        registro_pro_bolivia=f"70000{index:04d}",
        nombres_representante="Representante",
        apellido_paterno_representante=f"Demo{index}",
        apellido_materno_representante="Prueba",
        departamento=department,
        direccion_fisica=f"Zona productiva, calle Demo {index}",
        telefono_whatsapp=f"70000{index:03d}",
        correo_electronico=email,
        resena_comercial=f"{name} ofrece productos bolivianos elaborados con identidad local y calidad.",
        logo_url=logo_url,
        estado=RegistrationStatus.APPROVED,
        fecha_revision=datetime.now(timezone.utc),
        reviewed_by=admin.id,
    )
    db.session.add(registration)
    db.session.flush()

    sector = ensure_sector(sector_name)
    db.session.add(RegistrationRequestSector(
        registration_request_id=registration.id,
        productive_sector_id=sector.id,
    ))
    unit = ProductiveUnit(
        user_id=user.id,
        registration_request_id=registration.id,
        nombre_comercial=name,
        razon_social=f"{name} SRL",
        nit=registration.nit,
        registro_seprec=registration.registro_seprec,
        registro_pro_bolivia=registration.registro_pro_bolivia,
        nombres_representante=registration.nombres_representante,
        apellido_paterno_representante=registration.apellido_paterno_representante,
        apellido_materno_representante=registration.apellido_materno_representante,
        departamento=department,
        direccion_fisica=registration.direccion_fisica,
        telefono_whatsapp=registration.telefono_whatsapp,
        correo_electronico=email,
        resena_comercial=registration.resena_comercial,
        logo_url=logo_url,
        estado=ProductiveUnitStatus.ACTIVE,
        fecha_aprobacion=datetime.now(timezone.utc),
    )
    db.session.add(unit)
    db.session.flush()
    db.session.add(UnitSector(
        productive_unit_id=unit.id,
        productive_sector_id=sector.id,
        estado=SectorStatus.ACTIVE,
    ))
    return unit


def ensure_public_products(unit: ProductiveUnit, image_urls: list[str]):
    publicable = db.session.scalars(Product.publicable_query(unit.id)).all()
    for number in range(len(publicable) + 1, 4):
        product = Product(
            productive_unit_id=unit.id,
            nombre=f"Producto {number} de {unit.nombre_comercial}",
            nombre_comercial=f"Producto artesanal {number}",
            slug=f"demo-{str(unit.id)[:8]}-{number}",
            descripcion="Producto boliviano de demostración para el catálogo público.",
            descripcion_tecnica="Elaborado localmente con materia prima nacional y control de calidad.",
            materiales_o_ingredientes="Materia prima nacional",
            materia_prima="Materia prima seleccionada",
            lugar_origen=unit.departamento,
            presentacion="Presentación individual",
            presentacion_empaque="Empaque listo para entrega",
            precio_referencia=25 + number * 10,
            precio=25 + number * 10,
            capacidad_produccion_stock="100 unidades disponibles",
            estado=ProductStatus.AVAILABLE,
        )
        db.session.add(product)
        db.session.flush()
        for order in range(3):
            url = image_urls[(number + order - 1) % len(image_urls)]
            db.session.add(ProductImage(
                product_id=product.id,
                filename=Path(url).name,
                url=url,
                alt_text=f"{product.nombre_comercial} - vista {order + 1}",
                is_cover=order == 0,
                display_order=order,
            ))


def main():
    app = create_app()
    with app.app_context():
        admin = db.session.scalar(select(User).where(User.role.in_([
            Role.SUPERADMIN, Role.ADMIN_VICEMINISTERIO, Role.ADMIN,
        ])).order_by(User.created_at))
        if not admin:
            raise RuntimeError("Debe existir un administrador antes de cargar los datos demo")

        upload_root = Path(app.config["CARPETA_CARGAS"])
        fair_images = media_urls(upload_root, "ferias")
        logo_urls = media_urls(upload_root, "logos")
        image_urls = media_urls(upload_root, "productos") + logo_urls + fair_images
        if len(image_urls) < 3:
            raise RuntimeError("Se necesitan al menos tres imágenes locales para los productos demo")

        today = bolivia_today()
        target_fair_count = len(FAIR_DATA)
        active_fairs = db.session.scalars(Fair.active_query().order_by(Fair.created_at)).all()
        placeholder = next((fair for fair in active_fairs if len(fair.nombre.strip()) <= 2), None)
        fair_specs = list(FAIR_DATA)
        if placeholder and fair_specs:
            name, location, department, _municipality, description = fair_specs.pop(0)
            placeholder.nombre = name
            placeholder.slug = slugify(name)
            placeholder.ubicacion = placeholder.lugar = location
            placeholder.departamento = department
            placeholder.descripcion = description
            placeholder.fecha_inicio = today - timedelta(days=2)
            placeholder.fecha_fin = today + timedelta(days=12)
            placeholder.imagen_portada = fair_images[0] if fair_images else placeholder.imagen_portada

        active_fairs = db.session.scalars(Fair.active_query().order_by(Fair.created_at)).all()
        while len(active_fairs) < target_fair_count:
            spec = fair_specs.pop(0)
            name, location, department, _municipality, description = spec
            fair = Fair(
                nombre=name,
                slug=slugify(name),
                descripcion=description,
                ubicacion=location,
                lugar=location,
                departamento=department,
                fecha_inicio=today - timedelta(days=2),
                fecha_fin=today + timedelta(days=12),
                imagen_portada=fair_images[len(active_fairs) % len(fair_images)] if fair_images else None,
                estado=FeriaStatus.PUBLISHED,
                visible_publicamente=True,
                created_by=admin.id,
            )
            db.session.add(fair)
            db.session.flush()
            active_fairs.append(fair)

        password_hash = ph.hash("Demo.Publico2026!")
        units = db.session.scalars(
            select(ProductiveUnit).where(ProductiveUnit.deleted_at.is_(None)).order_by(ProductiveUnit.created_at)
        ).all()
        for index, data in enumerate(UNIT_DATA, start=1):
            if len(units) >= 10:
                break
            unit = create_demo_unit(index, data, admin, logo_urls, password_hash)
            if unit not in units:
                units.append(unit)

        for index, unit in enumerate(units[:10]):
            unit.estado = ProductiveUnitStatus.ACTIVE
            ensure_public_products(unit, image_urls)
            target_fair = active_fairs[index % target_fair_count]
            participation = db.session.scalar(select(FairParticipation).where(
                FairParticipation.fair_id == target_fair.id,
                FairParticipation.productive_unit_id == unit.id,
            ))
            if not participation:
                participation = FairParticipation(
                    fair_id=target_fair.id,
                    productive_unit_id=unit.id,
                )
                db.session.add(participation)
            participation.estado = AssignmentStatus.AUTHORIZED
            participation.authorized_by = admin.id
            participation.authorized_at = datetime.now(timezone.utc)
            participation.revoked_at = None

        for participation in db.session.scalars(select(FairParticipation).where(
            FairParticipation.fair_id.in_([fair.id for fair in active_fairs[:target_fair_count]]),
            FairParticipation.productive_unit_id.in_([unit.id for unit in units[:10]]),
        )).all():
            participation.estado = AssignmentStatus.AUTHORIZED
            participation.authorized_by = admin.id
            participation.authorized_at = participation.authorized_at or datetime.now(timezone.utc)
            participation.revoked_at = None

        invalidate_public_cache()
        db.session.commit()
        counts = []
        for fair in active_fairs[:target_fair_count]:
            count = len(db.session.scalars(select(FairParticipation).where(
                FairParticipation.fair_id == fair.id,
                FairParticipation.estado == AssignmentStatus.AUTHORIZED,
            )).all())
            counts.append(f"{fair.nombre}: {count} expositores")
        print("Datos públicos de demostración creados correctamente")
        print(" | ".join(counts))
        public_product_count = len(
            db.session.scalars(
                select(Product.id).where(Product.estado == ProductStatus.AVAILABLE)
            ).all()
        )
        print(
            f"Unidades productivas disponibles: {len(units[:10])}; "
            f"productos públicos: {public_product_count}"
        )


if __name__ == "__main__":
    main()
