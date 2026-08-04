"""Crea datos locales idempotentes para probar el portal publico."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app import create_app
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
from app.servicios import invalidate_public_cache
from app.utilidades import slugify


PRODUCT_TARGET = 15
FAIR_TARGET = 15


FAIR_DATA = (
    (
        "Feria Productiva del Altiplano",
        "Plaza Villarroel, pabellon productivo",
        "La Paz",
        "La Paz",
        "Produccion, identidad y emprendimiento boliviano.",
    ),
    (
        "Encuentro Nacional de Emprendedores",
        "Campo Ferial Alalay",
        "Cochabamba",
        "Cochabamba",
        "Productos nacionales y contacto directo con sus productores.",
    ),
    (
        "Ruta Andina de Sabores",
        "Coliseo Cerrado de El Alto",
        "La Paz",
        "El Alto",
        "Alimentos regionales, bebidas y degustaciones para catalogo y ventas.",
    ),
    (
        "Feria Textil de los Valles",
        "Centro de Convenciones FexpoSucre",
        "Chuquisaca",
        "Sucre",
        "Tejidos, confeccion y colecciones para pruebas de paginacion.",
    ),
    (
        "Expo Cuero y Moda",
        "Recinto Ferial Chuquiago Marka",
        "La Paz",
        "La Paz",
        "Cuero, calzados y accesorios con identidad nacional.",
    ),
    (
        "Feria de Artesania del Oriente",
        "Campo Ferial de Trinidad",
        "Beni",
        "Trinidad",
        "Artesanias y decoracion producidas en la region oriental.",
    ),
    (
        "Encuentro de Cosmetica Natural",
        "Casa de la Cultura",
        "Oruro",
        "Oruro",
        "Cosmetica, bienestar y cuidado personal de origen local.",
    ),
    (
        "Mercado Productivo del Sur",
        "Coliseo Universitario",
        "Tarija",
        "Tarija",
        "Productos del sur para exhibicion y prueba de catalogo.",
    ),
    (
        "Expo Orfebre Nacional",
        "Centro de Eventos Potosi",
        "Potosi",
        "Potosi",
        "Joyeria y orfebreria para cargar muchas participaciones.",
    ),
    (
        "Feria de Innovacion Artesanal",
        "Plaza Principal",
        "Cochabamba",
        "Cochabamba",
        "Prototipos, innovacion y artesania para la demo.",
    ),
    (
        "Jornada de Microempresas",
        "Centro Ferial de Montero",
        "Santa Cruz",
        "Montero",
        "Microempresas y emprendimientos en expansion.",
    ),
    (
        "Feria de Productos Naturales",
        "Parque Urbano Central",
        "La Paz",
        "La Paz",
        "Productos naturales para mostrar mas catalogo.",
    ),
    (
        "Encuentro de Emprendimientos del Chaco",
        "Centro Cultural",
        "Chuquisaca",
        "Monteagudo",
        "Emprendimientos del Chaco y ferias itinerantes.",
    ),
    (
        "Expo Sabores del Norte",
        "Polideportivo Municipal",
        "Beni",
        "Riberalta",
        "Sabores del norte para probar la paginacion.",
    ),
    (
        "Encuentro de Emprendedores Bolivianos",
        "Estadio Municipal",
        "Santa Cruz",
        "Warnes",
        "Encuentro nacional para pruebas extensas.",
    ),
)


UNIT_DATA = (
    ("Sabores del Valle", "Alimentos y Bebidas Procesados", "Cochabamba"),
    ("Tejidos Jach'a", "Textiles y Confecciones", "La Paz"),
    ("Madera Viva Bolivia", "Madera y Carpinteria", "Santa Cruz"),
    ("Manos de Tarija", "Artesania Tradicional o Decorativa", "Tarija"),
    ("Belleza Natural Andina", "Cosmetica Natural y Cuidado Personal", "Oruro"),
    ("Cuero Chapaco", "Cuero y Calzados", "Tarija"),
    ("Joyas del Salar", "Orfebreria y Joyeria", "Potosi"),
    ("Dulces de Sucre", "Alimentos y Bebidas Procesados", "Chuquisaca"),
    ("Arte Amazonico", "Artesania Tradicional o Decorativa", "Beni"),
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
    nit = f"90000{index:04d}"
    existing = db.session.scalar(select(ProductiveUnit).where(ProductiveUnit.correo_electronico == email))
    if existing:
        return existing

    user = db.session.scalar(
        select(User).where((User.email == email) | (User.username == f"expositor.demo{index:02d}"))
    )
    if not user:
        user = User(
            username=f"expositor.demo{index:02d}",
            email=email,
            password_hash=password_hash,
            role=Role.PRODUCTIVE_UNIT_RESPONSIBLE,
            first_name="Expositor",
            last_name=f"Demostracion {index}",
            apellido_paterno="Demostracion",
            apellido_materno="",
            phone=f"70000{index:03d}",
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        db.session.add(user)
        db.session.flush()
    else:
        user.username = f"expositor.demo{index:02d}"
        user.email = email
        user.role = Role.PRODUCTIVE_UNIT_RESPONSIBLE
        user.first_name = "Expositor"
        user.last_name = f"Demostracion {index}"
        user.apellido_paterno = "Demostracion"
        user.apellido_materno = ""
        user.phone = f"70000{index:03d}"
        user.status = UserStatus.ACTIVE
        user.must_change_password = False

    logo_url = logo_urls[(index - 1) % len(logo_urls)] if logo_urls else None
    registration = db.session.scalar(
        select(RegistrationRequest).where(
            (RegistrationRequest.correo_electronico == email) | (RegistrationRequest.nit == nit)
        )
    )
    if not registration:
        registration = RegistrationRequest(
            nombre_comercial=name,
            razon_social=f"{name} SRL",
            nit=nit,
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
    else:
        registration.nombre_comercial = name
        registration.razon_social = f"{name} SRL"
        registration.nit = nit
        registration.registro_seprec = f"80000{index:04d}"
        registration.registro_pro_bolivia = f"70000{index:04d}"
        registration.nombres_representante = "Representante"
        registration.apellido_paterno_representante = f"Demo{index}"
        registration.apellido_materno_representante = "Prueba"
        registration.departamento = department
        registration.direccion_fisica = f"Zona productiva, calle Demo {index}"
        registration.telefono_whatsapp = f"70000{index:03d}"
        registration.correo_electronico = email
        registration.resena_comercial = (
            f"{name} ofrece productos bolivianos elaborados con identidad local y calidad."
        )
        registration.logo_url = logo_url
        registration.estado = RegistrationStatus.APPROVED
        registration.fecha_revision = datetime.now(timezone.utc)
        registration.reviewed_by = admin.id

    sector = ensure_sector(sector_name)
    db.session.add(
        RegistrationRequestSector(
            registration_request_id=registration.id,
            productive_sector_id=sector.id,
        )
    )
    unit = db.session.scalar(
        select(ProductiveUnit).where(
            (ProductiveUnit.correo_electronico == email)
            | (ProductiveUnit.nit == nit)
            | (ProductiveUnit.registration_request_id == registration.id)
        )
    )
    if not unit:
        unit = ProductiveUnit(
            user_id=user.id,
            registration_request_id=registration.id,
            nombre_comercial=name,
            razon_social=f"{name} SRL",
            nit=nit,
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
    else:
        unit.user_id = user.id
        unit.registration_request_id = registration.id
        unit.nombre_comercial = name
        unit.razon_social = f"{name} SRL"
        unit.nit = nit
        unit.registro_seprec = registration.registro_seprec
        unit.registro_pro_bolivia = registration.registro_pro_bolivia
        unit.nombres_representante = registration.nombres_representante
        unit.apellido_paterno_representante = registration.apellido_paterno_representante
        unit.apellido_materno_representante = registration.apellido_materno_representante
        unit.departamento = department
        unit.direccion_fisica = registration.direccion_fisica
        unit.telefono_whatsapp = registration.telefono_whatsapp
        unit.correo_electronico = email
        unit.resena_comercial = registration.resena_comercial
        unit.logo_url = logo_url
        unit.estado = ProductiveUnitStatus.ACTIVE
        unit.deleted_at = None
    db.session.add(
        UnitSector(
            productive_unit_id=unit.id,
            productive_sector_id=sector.id,
            estado=SectorStatus.ACTIVE,
        )
    )
    return unit


def ensure_public_products(unit: ProductiveUnit, image_urls: list[str]):
    publicable = db.session.scalars(Product.publicable_query(unit.id)).all()
    for number in range(len(publicable) + 1, PRODUCT_TARGET + 1):
        product = Product(
            productive_unit_id=unit.id,
            nombre=f"Producto {number} de {unit.nombre_comercial}",
            nombre_comercial=f"Producto artesanal {number}",
            slug=f"demo-{str(unit.id)[:8]}-{number}",
            descripcion="Producto boliviano de demostracion para el catalogo publico.",
            descripcion_tecnica="Elaborado localmente con materia prima nacional y control de calidad.",
            materiales_o_ingredientes="Materia prima nacional",
            materia_prima="Materia prima seleccionada",
            lugar_origen=unit.departamento,
            presentacion="Presentacion individual",
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
            db.session.add(
                ProductImage(
                    product_id=product.id,
                    filename=Path(url).name,
                    url=url,
                    alt_text=f"{product.nombre_comercial} - vista {order + 1}",
                    is_cover=order == 0,
                    display_order=order,
                )
            )


def main():
    app = create_app()
    with app.app_context():
        admin = db.session.scalar(
            select(User).where(User.role == Role.ADMIN).order_by(User.created_at)
        )
        if not admin:
            raise RuntimeError("Debe existir un administrador antes de cargar los datos demo")

        upload_root = Path(app.config["CARPETA_CARGAS"])
        fair_images = media_urls(upload_root, "ferias")
        logo_urls = media_urls(upload_root, "logos")
        image_urls = media_urls(upload_root, "productos") + logo_urls + fair_images
        if len(image_urls) < 3:
            raise RuntimeError("Se necesitan al menos tres imagenes locales para los productos demo")

        today = bolivia_today()
        now_utc = datetime.now(timezone.utc)
        def ensure_fair(name, location, department, description, starts_in, ends_in, status):
            fair = db.session.scalar(select(Fair).where(Fair.slug == slugify(name)))
            cover = fair_images[0] if fair_images else None
            if not fair:
                fair = Fair(
                    nombre=name,
                    slug=slugify(name),
                    descripcion=description,
                    ubicacion=location,
                    lugar=location,
                    departamento=department,
                    fecha_inicio=today + timedelta(days=starts_in),
                    fecha_fin=today + timedelta(days=ends_in),
                    fecha_limite_registro=today + timedelta(days=max(starts_in - 3, -1)),
                    imagen_portada=cover,
                    estado=status,
                    visible_publicamente=status == FeriaStatus.PUBLISHED,
                    created_by=admin.id,
                    disabled_at=now_utc if status == FeriaStatus.DISABLED else None,
                    finished_at=now_utc if status == FeriaStatus.FINISHED else None,
                )
                db.session.add(fair)
                db.session.flush()
                return fair
            fair.nombre = name
            fair.descripcion = description
            fair.ubicacion = location
            fair.lugar = location
            fair.departamento = department
            fair.fecha_inicio = today + timedelta(days=starts_in)
            fair.fecha_fin = today + timedelta(days=ends_in)
            fair.fecha_limite_registro = today + timedelta(days=max(starts_in - 3, -1))
            fair.imagen_portada = fair.imagen_portada or cover
            fair.estado = status
            fair.visible_publicamente = status == FeriaStatus.PUBLISHED
            fair.deleted_at = None
            fair.disabled_at = now_utc if status == FeriaStatus.DISABLED else None
            fair.finished_at = now_utc if status == FeriaStatus.FINISHED else None
            return fair

        demo_fairs = [
            ensure_fair(
                name,
                location,
                department,
                description,
                -5 + index,
                8 + index,
                FeriaStatus.PUBLISHED,
            )
            for index, (name, location, department, _municipality, description) in enumerate(FAIR_DATA)
        ]

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

        for unit in units[:10]:
            unit.estado = ProductiveUnitStatus.ACTIVE
            ensure_public_products(unit, image_urls)
            for target_fair in demo_fairs:
                participation = db.session.scalar(
                    select(FairParticipation).where(
                        FairParticipation.fair_id == target_fair.id,
                        FairParticipation.productive_unit_id == unit.id,
                    )
                )
                if not participation:
                    participation = FairParticipation(
                        fair_id=target_fair.id,
                        productive_unit_id=unit.id,
                    )
                    db.session.add(participation)
                participation.estado = AssignmentStatus.AUTHORIZED
                participation.authorized_by = admin.id
                participation.authorized_at = now_utc
                participation.revoked_at = None

        for participation in db.session.scalars(
            select(FairParticipation).where(
                FairParticipation.fair_id.in_([fair.id for fair in demo_fairs]),
                FairParticipation.productive_unit_id.in_([unit.id for unit in units[:10]]),
            )
        ).all():
            participation.estado = AssignmentStatus.AUTHORIZED
            participation.authorized_by = admin.id
            participation.authorized_at = participation.authorized_at or now_utc
            participation.revoked_at = None

        invalidate_public_cache()
        db.session.commit()
        counts = []
        for fair in demo_fairs:
            count = len(
                db.session.scalars(
                    select(FairParticipation).where(
                        FairParticipation.fair_id == fair.id,
                        FairParticipation.estado == AssignmentStatus.AUTHORIZED,
                    )
                ).all()
            )
            counts.append(f"{fair.nombre}: {count} expositores")
        print("Datos publicos de demostracion creados correctamente")
        print(" | ".join(counts))
        public_product_count = len(
            db.session.scalars(select(Product.id).where(Product.estado == ProductStatus.AVAILABLE)).all()
        )
        print(
            f"Unidades productivas disponibles: {len(units[:10])}; "
            f"productos publicos: {public_product_count}"
        )


if __name__ == "__main__":
    main()
