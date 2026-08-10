from datetime import datetime, timedelta, timezone
import os
import re
from pathlib import Path

import click
from flask.cli import with_appcontext
from sqlalchemy import delete, select, text
from sqlalchemy.engine import make_url

from .extensiones import db
from .modelos import (
    AssignmentStatus,
    Category,
    ExhibitorType,
    Fair,
    FairParticipation,
    FeriaStatus,
    NotificationStatus,
    Product,
    ProductImage,
    ProductStatus,
    ProductiveSector,
    ProductiveUnit,
    ProductiveUnitStatus,
    RegistrationRequest,
    RegistrationRequestProduct,
    RegistrationRequestSector,
    RegistrationStatus,
    RevokedToken,
    Role,
    SectorStatus,
    UnitSector,
    User,
    UserStatus,
    bolivia_today,
)
from .modelos.usuario import ph
from .servicios import invalidate_public_cache
from .utilidades import slugify, valid_gmail


def registrar_comandos(app):
    @app.cli.command("sync-fairs")
    @with_appcontext
    def sync_fairs():
        from .servicios import audit, managed_upload_path
        from .rutas.ferias import sync_fair_lifecycle

        changed = sync_fair_lifecycle()
        expired_tokens = db.session.execute(
            delete(RevokedToken).where(
                RevokedToken.expires_at <= datetime.now(timezone.utc)
            )
        ).rowcount
        db.session.commit()
        urls = [
            *db.session.scalars(
                select(Fair.imagen_portada).where(Fair.imagen_portada.is_not(None))
            ).all(),
        ]
        referenced = {
            path.resolve()
            for url in urls
            if (path := managed_upload_path(url, "ferias"))
        }
        folder = Path(app.config["CARPETA_CARGAS"]) / "ferias"
        removed = 0
        if folder.exists():
            for path in folder.iterdir():
                if path.is_file() and path.resolve() not in referenced:
                    path.unlink()
                    removed += 1
        audit(
            "SINCRONIZAR_FERIAS",
            "Fair",
            after={
                "estados_actualizados": bool(changed),
                "tokens_expirados_eliminados": expired_tokens,
                "archivos_huerfanos_eliminados": removed,
            },
        )
        db.session.commit()
        click.echo(
            f"Ferias: {'actualizadas' if changed else 'sin cambios'}; "
            f"archivos huérfanos eliminados: {removed}"
        )

        click.echo(f"Tokens revocados expirados eliminados: {expired_tokens}")

    def require_postgresql_test_database():
        url = make_url(app.config["SQLALCHEMY_DATABASE_URI"])
        database_name = url.database or ""
        if url.get_backend_name() != "postgresql" or not database_name.endswith("_test"):
            raise click.ClickException(
                "Este comando solo acepta PostgreSQL y una base cuyo nombre termine en _test"
            )

    @app.cli.command("reset-test-db")
    @click.option("--yes", is_flag=True)
    @with_appcontext
    def reset_test_db(yes):
        """Reconstruye una base PostgreSQL de prueba desde las migraciones."""
        require_postgresql_test_database()
        if not yes:
            raise click.ClickException("Confirme la operación con --yes")
        db.session.execute(text("DROP SCHEMA public CASCADE"))
        db.session.execute(text("CREATE SCHEMA public"))
        db.session.commit()
        from flask_migrate import upgrade

        upgrade()
        click.echo("Base de prueba reconstruida desde migraciones")

    @app.cli.command("seed-test-data")
    @with_appcontext
    def seed_test_data():
        """Carga una base de pruebas amplia e idempotente."""
        require_postgresql_test_database()
        email = os.getenv("CORREO_ADMINISTRADOR_PRUEBAS", "catalogo.test@gmail.com").lower()
        password = os.getenv("CONTRASENA_ADMINISTRADOR_PRUEBAS", "")
        if not password:
            raise click.ClickException(
                "Configure CONTRASENA_ADMINISTRADOR_PRUEBAS para cargar datos de prueba"
            )
        now_utc = datetime.now(timezone.utc)
        today = bolivia_today()

        def ensure_admin(
            *, username, email_address, first_name, paternal_last_name, maternal_last_name,
            status=UserStatus.ACTIVE, must_change_password=False, raw_password=password
        ):
            user = db.session.scalar(
                select(User).where(
                    (User.email == email_address.lower()) | (User.username == username.lower())
                )
            )
            if not user:
                user = User(
                    username=username.lower(),
                    email=email_address.lower(),
                    role=Role.ADMIN,
                    first_name=first_name,
                    last_name=paternal_last_name,
                    apellido_paterno=paternal_last_name,
                    apellido_materno=maternal_last_name,
                    status=status,
                    must_change_password=must_change_password,
                )
                user.set_password(raw_password)
                db.session.add(user)
                db.session.flush()
                return user
            if user.role != Role.ADMIN:
                raise click.ClickException(
                    f"El usuario {user.username} ya existe con un rol distinto a ADMIN"
                )
            user.first_name = first_name
            user.last_name = paternal_last_name
            user.apellido_paterno = paternal_last_name
            user.apellido_materno = maternal_last_name
            user.status = status
            user.must_change_password = must_change_password
            return user

        def ensure_sector(name, description=None, is_other=False):
            sector = db.session.scalar(
                select(ProductiveSector).where(ProductiveSector.nombre == name)
            )
            if sector:
                sector.descripcion = description or sector.descripcion
                sector.es_otro = is_other
                sector.estado = SectorStatus.ACTIVE
                sector.deleted_at = None
                return sector
            sector = ProductiveSector(
                nombre=name,
                descripcion=description,
                estado=SectorStatus.ACTIVE,
                es_otro=is_other,
            )
            db.session.add(sector)
            db.session.flush()
            return sector

        def ensure_category(name):
            category = db.session.scalar(select(Category).where(Category.nombre == name))
            if category:
                category.estado = True
                category.deleted_at = None
                return category
            category = Category(nombre=name, slug=slugify(name), estado=True)
            db.session.add(category)
            db.session.flush()
            return category

        def media_urls(folder):
            target = Path(app.config["CARPETA_CARGAS"]) / folder
            if not target.is_dir():
                return []
            return [
                f"/uploads/{folder}/{path.name}"
                for path in sorted(target.iterdir())
                if path.is_file()
            ]

        primary_admin = ensure_admin(
            username="catalogo.test",
            email_address=email,
            first_name="Administrador",
            paternal_last_name="Pruebas",
            maternal_last_name="Sistema",
            status=UserStatus.ACTIVE,
            must_change_password=False,
        )
        ensure_admin(
            username="maria.rivera",
            email_address="maria.rivera@fcpn.edu.bo",
            first_name="Maria",
            paternal_last_name="Rivera",
            maternal_last_name="Lopez",
            status=UserStatus.ACTIVE,
            must_change_password=True,
            raw_password=password,
        )
        ensure_admin(
            username="jorge.quispe",
            email_address="jorge.quispe@fcpn.edu.bo",
            first_name="Jorge",
            paternal_last_name="Quispe",
            maternal_last_name="Mamani",
            status=UserStatus.INACTIVE,
            must_change_password=False,
            raw_password=password,
        )

        for name in [
            "Microempresa",
            "Productor",
            "Artesano",
            "Emprendimiento",
            "Asociacion",
            "Cooperativa",
            "Otro",
        ]:
            if not db.session.scalar(
                select(ExhibitorType.id).where(ExhibitorType.nombre == name)
            ):
                db.session.add(ExhibitorType(nombre=name))

        for name in [
            "Alimentos",
            "Artesanias",
            "Textiles",
            "Cosmetica natural",
            "Bebidas",
            "Marroquineria",
            "Otros",
        ]:
            ensure_category(name)

        sectors = [
            ("Textiles y Confecciones", "Produccion textil y confecciones nacionales."),
            ("Cuero y Calzados", "Manufactura de cuero, calzado y derivados."),
            ("Alimentos y Bebidas Procesados", "Produccion alimentaria con valor agregado."),
            ("Madera y Carpinteria", "Muebles, carpinteria y acabados en madera."),
            ("Orfebreria y Joyeria", "Joyeria artesanal y orfebreria boliviana."),
            ("Cosmetica Natural y Cuidado Personal", "Productos de bienestar y cosmetica natural."),
            ("Artesania Tradicional o Decorativa", "Artesanias con identidad regional."),
            ("Otros", "Sector abierto para pruebas adicionales."),
        ]
        for name, description in sectors:
            ensure_sector(name, description, is_other=name == "Otros")

        fair_images = media_urls("ferias")
        product_images = media_urls("productos")
        logo_images = media_urls("logos")
        request_images = media_urls("solicitudes") or product_images
        shared_images = product_images + logo_images + fair_images
        if not shared_images:
            raise click.ClickException(
                "No se encontraron imagenes en backend/uploads para completar los datos de prueba"
            )

        def ensure_fair(name, *, location, department, description, starts_in, ends_in, status):
            fair = db.session.scalar(select(Fair).where(Fair.slug == slugify(name)))
            if not fair:
                fair = Fair(
                    nombre=name,
                    slug=slugify(name),
                    descripcion=description,
                    lugar=location,
                    ubicacion=location,
                    departamento=department,
                    fecha_inicio=today + timedelta(days=starts_in),
                    fecha_fin=today + timedelta(days=ends_in),
                    fecha_limite_registro=today + timedelta(days=max(starts_in - 3, -1)),
                    imagen_portada=fair_images[0] if fair_images else None,
                    estado=status,
                    visible_publicamente=status == FeriaStatus.PUBLISHED,
                    created_by=primary_admin.id,
                    disabled_at=now_utc if status == FeriaStatus.DISABLED else None,
                    finished_at=now_utc if status == FeriaStatus.FINISHED else None,
                )
                db.session.add(fair)
                db.session.flush()
                return fair
            fair.nombre = name
            fair.descripcion = description
            fair.lugar = location
            fair.ubicacion = location
            fair.departamento = department
            fair.fecha_inicio = today + timedelta(days=starts_in)
            fair.fecha_fin = today + timedelta(days=ends_in)
            fair.fecha_limite_registro = today + timedelta(days=max(starts_in - 3, -1))
            fair.imagen_portada = fair.imagen_portada or (fair_images[0] if fair_images else None)
            fair.estado = status
            fair.visible_publicamente = status == FeriaStatus.PUBLISHED
            fair.deleted_at = None
            fair.disabled_at = now_utc if status == FeriaStatus.DISABLED else None
            fair.finished_at = now_utc if status == FeriaStatus.FINISHED else None
            return fair

        published_fair = ensure_fair(
            "Feria Productiva del Altiplano",
            location="Plaza Villarroel, pabellon productivo",
            department="La Paz",
            description="Produccion, identidad y emprendimiento boliviano.",
            starts_in=-2,
            ends_in=12,
            status=FeriaStatus.PUBLISHED,
        )
        demo_fair_specs = [
            (
                "Encuentro Nacional de Emprendedores",
                "Campo Ferial Alalay",
                "Cochabamba",
                "Productos nacionales y contacto directo con sus productores.",
                10,
                16,
                FeriaStatus.DRAFT,
            ),
            (
                "Feria Hecho en Bolivia 2026",
                "Parque Urbano Central",
                "La Paz",
                "Evento concluido para probar estados finalizados.",
                -25,
                -12,
                FeriaStatus.FINISHED,
            ),
            (
                "Expo Regiones Integradas",
                "Fexpocruz",
                "Santa Cruz",
                "Feria deshabilitada para pruebas administrativas.",
                20,
                26,
                FeriaStatus.DISABLED,
            ),
            (
                "Ruta Andina de Sabores",
                "Coliseo Cerrado de El Alto",
                "La Paz",
                "Alimentos regionales y bebidas para pruebas de paginacion.",
                -5,
                8,
                FeriaStatus.PUBLISHED,
            ),
            (
                "Feria Textil de los Valles",
                "Centro de Convenciones FexpoSucre",
                "Chuquisaca",
                "Tejidos, confeccion y colecciones para pruebas de catalogo.",
                -4,
                9,
                FeriaStatus.PUBLISHED,
            ),
            (
                "Expo Cuero y Moda",
                "Recinto Ferial Chuquiago Marka",
                "La Paz",
                "Cuero, calzados y accesorios con identidad nacional.",
                -3,
                10,
                FeriaStatus.PUBLISHED,
            ),
            (
                "Feria de Artesania del Oriente",
                "Campo Ferial de Trinidad",
                "Beni",
                "Artesanias y decoracion producidas en la region oriental.",
                -2,
                11,
                FeriaStatus.PUBLISHED,
            ),
            (
                "Encuentro de Cosmetica Natural",
                "Casa de la Cultura",
                "Oruro",
                "Cosmetica, bienestar y cuidado personal de origen local.",
                -1,
                12,
                FeriaStatus.PUBLISHED,
            ),
            (
                "Mercado Productivo del Sur",
                "Coliseo Universitario",
                "Tarija",
                "Productos del sur para exhibicion y prueba de catalogo.",
                1,
                14,
                FeriaStatus.PUBLISHED,
            ),
            (
                "Expo Orfebre Nacional",
                "Centro de Eventos Potosi",
                "Potosi",
                "Joyeria y orfebreria para cargar muchas participaciones.",
                2,
                15,
                FeriaStatus.PUBLISHED,
            ),
            (
                "Feria de Innovacion Artesanal",
                "Plaza Principal",
                "Cochabamba",
                "Prototipos, innovacion y artesania para la demo.",
                3,
                16,
                FeriaStatus.PUBLISHED,
            ),
            (
                "Jornada de Microempresas",
                "Centro Ferial de Montero",
                "Santa Cruz",
                "Microempresas y emprendimientos en expansion.",
                4,
                17,
                FeriaStatus.PUBLISHED,
            ),
            (
                "Feria de Productos Naturales",
                "Parque Urbano Central",
                "La Paz",
                "Productos naturales para mostrar mas catalogo.",
                5,
                18,
                FeriaStatus.PUBLISHED,
            ),
            (
                "Encuentro de Emprendimientos del Chaco",
                "Centro Cultural",
                "Chuquisaca",
                "Emprendimientos del Chaco y ferias itinerantes.",
                6,
                19,
                FeriaStatus.PUBLISHED,
            ),
            (
                "Encuentro de Emprendedores Bolivianos",
                "Estadio Municipal",
                "Santa Cruz",
                "Encuentro nacional para pruebas extensas.",
                7,
                20,
                FeriaStatus.PUBLISHED,
            ),
        ]
        demo_fairs = [published_fair]
        for fair_name, location, department, description, starts_in, ends_in, status in demo_fair_specs:
            demo_fairs.append(
                ensure_fair(
                    fair_name,
                    location=location,
                    department=department,
                    description=description,
                    starts_in=starts_in,
                    ends_in=ends_in,
                    status=status,
                )
            )

        category_ids = [
            item.id
            for item in db.session.scalars(
                select(Category).where(Category.deleted_at.is_(None)).order_by(Category.nombre)
            ).all()
        ]

        def ensure_demo_unit(index, data):
            name, sector_name, department = data
            email_address = f"expositor.demo{index:02d}@gmail.com"
            nit = f"99000{index:04d}"
            user = db.session.scalar(
                select(User).where(
                    (User.email == email_address) | (User.username == f"expositor.demo{index:02d}")
                )
            )
            if not user:
                user = User(
                    username=f"expositor.demo{index:02d}",
                    email=email_address,
                    password_hash=ph.hash("Demo.Publico2026!"),
                    role=Role.PRODUCTIVE_UNIT_RESPONSIBLE,
                    first_name="Representante",
                    last_name=f"Demo {index}",
                    apellido_paterno="Demo",
                    apellido_materno=f"Unidad {index}",
                    phone=f"70000{index:03d}",
                    status=UserStatus.ACTIVE,
                    must_change_password=False,
                )
                db.session.add(user)
                db.session.flush()
            else:
                user.username = f"expositor.demo{index:02d}"
                user.email = email_address
                user.role = Role.PRODUCTIVE_UNIT_RESPONSIBLE
                user.first_name = "Representante"
                user.last_name = f"Demo {index}"
                user.apellido_paterno = "Demo"
                user.apellido_materno = f"Unidad {index}"
                user.phone = f"70000{index:03d}"
                user.status = UserStatus.ACTIVE
                user.must_change_password = False

            sector = ensure_sector(sector_name)
            registration = db.session.scalar(
                select(RegistrationRequest).where(
                    (RegistrationRequest.correo_electronico == email_address)
                    | (RegistrationRequest.nit == nit)
                )
            )
            logo_url = logo_images[(index - 1) % len(logo_images)] if logo_images else None
            if not registration:
                registration = RegistrationRequest(
                    nombre_comercial=name,
                    razon_social=f"{name} SRL",
                    nit=nit,
                    registro_seprec=f"88000{index:04d}",
                    registro_pro_bolivia=f"77000{index:04d}",
                    nombres_representante="Mariela",
                    apellido_paterno_representante=f"Quispe{index}",
                    apellido_materno_representante="Mamani",
                    departamento=department,
                    direccion_fisica=f"Zona comercial {index}, avenida principal",
                    telefono_whatsapp=f"71234{index:03d}",
                    correo_electronico=email_address,
                    facebook_url=f"https://facebook.com/demo.unidad.{index:02d}",
                    instagram_url=f"https://instagram.com/demo.unidad.{index:02d}",
                    tiktok_url=f"https://tiktok.com/@demo.unidad.{index:02d}",
                    resena_comercial=f"{name} produce y comercializa bienes bolivianos.",
                    logo_url=logo_url,
                    estado=RegistrationStatus.APPROVED,
                    fecha_revision=now_utc,
                    reviewed_by=primary_admin.id,
                    notification_status=NotificationStatus.SENT,
                    credentials_sent_at=now_utc,
                )
                db.session.add(registration)
                db.session.flush()
            else:
                registration.nombre_comercial = name
                registration.razon_social = f"{name} SRL"
                registration.nit = nit
                registration.registro_seprec = f"88000{index:04d}"
                registration.registro_pro_bolivia = f"77000{index:04d}"
                registration.nombres_representante = "Mariela"
                registration.apellido_paterno_representante = f"Quispe{index}"
                registration.apellido_materno_representante = "Mamani"
                registration.departamento = department
                registration.direccion_fisica = f"Zona comercial {index}, avenida principal"
                registration.telefono_whatsapp = f"71234{index:03d}"
                registration.correo_electronico = email_address
                registration.facebook_url = f"https://facebook.com/demo.unidad.{index:02d}"
                registration.instagram_url = f"https://instagram.com/demo.unidad.{index:02d}"
                registration.tiktok_url = f"https://tiktok.com/@demo.unidad.{index:02d}"
                registration.resena_comercial = f"{name} produce y comercializa bienes bolivianos."
                registration.logo_url = logo_url
                registration.estado = RegistrationStatus.APPROVED
                registration.fecha_revision = now_utc
                registration.reviewed_by = primary_admin.id
                registration.notification_status = NotificationStatus.SENT
                registration.credentials_sent_at = now_utc
            if not db.session.scalar(
                select(RegistrationRequestSector.id).where(
                    RegistrationRequestSector.registration_request_id == registration.id,
                    RegistrationRequestSector.productive_sector_id == sector.id,
                )
            ):
                db.session.add(
                    RegistrationRequestSector(
                        registration_request_id=registration.id,
                        productive_sector_id=sector.id,
                    )
                )

            unit = db.session.scalar(
                select(ProductiveUnit).where(
                    (ProductiveUnit.registration_request_id == registration.id)
                    | (ProductiveUnit.correo_electronico == email_address)
                    | (ProductiveUnit.nit == nit)
                )
            )
            if not unit:
                unit = ProductiveUnit(
                    user_id=user.id,
                    registration_request_id=registration.id,
                    nombre_comercial=name,
                    razon_social=registration.razon_social,
                    nit=nit,
                    registro_seprec=registration.registro_seprec,
                    registro_pro_bolivia=registration.registro_pro_bolivia,
                    nombres_representante=registration.nombres_representante,
                    apellido_paterno_representante=registration.apellido_paterno_representante,
                    apellido_materno_representante=registration.apellido_materno_representante,
                    departamento=department,
                    direccion_fisica=registration.direccion_fisica,
                    telefono_whatsapp=registration.telefono_whatsapp,
                    correo_electronico=email_address,
                    facebook_url=registration.facebook_url,
                    instagram_url=registration.instagram_url,
                    tiktok_url=registration.tiktok_url,
                    resena_comercial=registration.resena_comercial,
                    logo_url=logo_url,
                    estado=ProductiveUnitStatus.ACTIVE,
                    fecha_aprobacion=now_utc,
                )
                db.session.add(unit)
                db.session.flush()
            else:
                unit.user_id = user.id
                unit.registration_request_id = registration.id
                unit.nombre_comercial = name
                unit.razon_social = registration.razon_social
                unit.nit = nit
                unit.registro_seprec = registration.registro_seprec
                unit.registro_pro_bolivia = registration.registro_pro_bolivia
                unit.nombres_representante = registration.nombres_representante
                unit.apellido_paterno_representante = registration.apellido_paterno_representante
                unit.apellido_materno_representante = registration.apellido_materno_representante
                unit.departamento = department
                unit.direccion_fisica = registration.direccion_fisica
                unit.telefono_whatsapp = registration.telefono_whatsapp
                unit.correo_electronico = email_address
                unit.facebook_url = registration.facebook_url
                unit.instagram_url = registration.instagram_url
                unit.tiktok_url = registration.tiktok_url
                unit.resena_comercial = registration.resena_comercial
                unit.logo_url = logo_url
                unit.estado = ProductiveUnitStatus.ACTIVE
                unit.deleted_at = None

            if not db.session.scalar(
                select(UnitSector.id).where(
                    UnitSector.productive_unit_id == unit.id,
                    UnitSector.productive_sector_id == sector.id,
                )
            ):
                db.session.add(
                    UnitSector(
                        productive_unit_id=unit.id,
                        productive_sector_id=sector.id,
                        estado=SectorStatus.ACTIVE,
                    )
                )

            products = db.session.scalars(
                select(Product)
                .where(Product.productive_unit_id == unit.id, Product.deleted_at.is_(None))
                .order_by(Product.created_at)
            ).all()
            if len(products) < 15:
                for number in range(len(products) + 1, 16):
                    product = Product(
                        productive_unit_id=unit.id,
                        category_id=category_ids[(index + number - 2) % len(category_ids)],
                        nombre=f"Producto {number} de {name}",
                        slug=f"{slugify(name)}-{number}",
                        descripcion=f"Producto de prueba del catalogo para {name}.",
                        materiales_o_ingredientes="Materia prima nacional seleccionada",
                        lugar_origen=department,
                        presentacion="Presentacion estandar",
                        informacion_adicional="Registro de ejemplo para pruebas funcionales.",
                        nombre_comercial=f"Linea comercial {number} de {name}",
                        descripcion_tecnica="Ficha tecnica de demostracion para validaciones del sistema.",
                        materia_prima="Materia prima local",
                        dimensiones="30 x 20 cm",
                        colores_disponibles="Rojo, azul, natural",
                        certificaciones="Registro interno de demostracion",
                        presentacion_empaque="Empaque listo para envio",
                        precio_referencia=20 + number * 7,
                        capacidad_produccion_stock="150 unidades por mes",
                        precio=20 + number * 7,
                        estado=(
                            ProductStatus.OUT_OF_STOCK
                            if number == 3 and index % 2 == 0
                            else ProductStatus.AVAILABLE
                        ),
                    )
                    db.session.add(product)
                    db.session.flush()
                    for order in range(3):
                        url = shared_images[(index + number + order - 2) % len(shared_images)]
                        db.session.add(
                            ProductImage(
                                product_id=product.id,
                                filename=Path(url).name,
                                url=url,
                                alt_text=f"{product.nombre} - imagen {order + 1}",
                                is_cover=order == 0,
                                display_order=order,
                            )
                        )
            return unit

        units = [
            ensure_demo_unit(index, spec)
            for index, spec in enumerate(
                (
                    ("Sabores del Valle", "Alimentos y Bebidas Procesados", "Cochabamba"),
                    ("Tejidos Jach'a", "Textiles y Confecciones", "La Paz"),
                    ("Madera Viva Bolivia", "Madera y Carpinteria", "Santa Cruz"),
                    ("Manos de Tarija", "Artesania Tradicional o Decorativa", "Tarija"),
                    ("Belleza Natural Andina", "Cosmetica Natural y Cuidado Personal", "Oruro"),
                    ("Cuero Chapaco", "Cuero y Calzados", "Tarija"),
                ),
                start=1,
            )
        ]

        for unit in units:
            for fair_index, fair in enumerate(demo_fairs):
                participation = db.session.scalar(
                    select(FairParticipation).where(
                        FairParticipation.fair_id == fair.id,
                        FairParticipation.productive_unit_id == unit.id,
                    )
                )
                if not participation:
                    participation = FairParticipation(
                        fair_id=fair.id,
                        productive_unit_id=unit.id,
                    )
                    db.session.add(participation)
                participation.estado = AssignmentStatus.AUTHORIZED
                participation.authorized_by = primary_admin.id
                participation.authorized_at = now_utc
                participation.revoked_at = None
                participation.observaciones = (
                    f"Participacion aprobada para demostracion #{fair_index + 1}."
                )

        qa_cases = (
            ("Pendiente", RegistrationStatus.PENDING, "qa.pendiente", None),
            ("Aprobada", RegistrationStatus.APPROVED, "qa.aprobada", None),
            (
                "Rechazada",
                RegistrationStatus.REJECTED,
                "qa.rechazada",
                "Caso QA rechazado: documentacion incompleta para la revision.",
            ),
        )
        qa_sector = ensure_sector(
            "QA - Sector de prueba",
            "Sector auxiliar para validar flujos administrativos.",
        )
        for label, status, prefix, reason in qa_cases:
            email_address = f"{prefix}@fcpn.edu.bo"
            request = db.session.scalar(
                select(RegistrationRequest).where(
                    RegistrationRequest.correo_electronico == email_address
                )
            )
            if request:
                continue
            request = RegistrationRequest(
                nombre_comercial=f"Solicitud QA {label}",
                razon_social=f"Solicitud QA {label} SRL",
                nit=f"98765{len(label):04d}",
                registro_seprec=f"87654{len(label):04d}",
                registro_pro_bolivia=f"76543{len(label):04d}",
                nombres_representante="Maria Fernanda",
                apellido_paterno_representante="Quispe",
                apellido_materno_representante="Mamani",
                departamento="La Paz",
                direccion_fisica="Av. QA 123, zona central",
                telefono_whatsapp="71234567",
                correo_electronico=email_address,
                facebook_url="https://facebook.com/qa.solicitud",
                instagram_url="https://instagram.com/qa.solicitud",
                tiktok_url="https://tiktok.com/@qa.solicitud",
                resena_comercial="Caso de prueba para revisar el flujo completo de solicitudes.",
                logo_url=request_images[0] if request_images else None,
                estado=status,
                reviewed_by=primary_admin.id if status != RegistrationStatus.PENDING else None,
                fecha_revision=now_utc if status != RegistrationStatus.PENDING else None,
                notification_status=(
                    NotificationStatus.SENT if status != RegistrationStatus.PENDING else None
                ),
                credentials_sent_at=now_utc if status == RegistrationStatus.APPROVED else None,
                motivo_rechazo=reason,
            )
            db.session.add(request)
            db.session.flush()
            db.session.add(
                RegistrationRequestSector(
                    registration_request_id=request.id,
                    productive_sector_id=qa_sector.id,
                )
            )
            if request_images:
                for order in range(1, 4):
                    db.session.add(
                        RegistrationRequestProduct(
                            registration_request_id=request.id,
                            nombre_comercial=f"Producto QA {order} - {label}",
                            descripcion_tecnica=(
                                "Descripcion tecnica de ejemplo para validar listados y detalle."
                            ),
                            precio_referencia=order * 25,
                            imagen_url=request_images[(order - 1) % len(request_images)],
                            orden=order,
                        )
                    )

        invalidate_public_cache()
        db.session.commit()
        click.echo(
            "Datos de prueba creados: "
            f"3 administradores, {len(units)} unidades productivas, {len(demo_fairs)} ferias y 3 solicitudes QA"
        )
        click.echo(f"Administrador principal: {email}")

    @app.cli.command("seed-admin")
    @with_appcontext
    def seed_admin():
        email = os.getenv("CORREO_ADMINISTRADOR_INICIAL", "").lower().strip()
        password = os.getenv("CONTRASENA_ADMINISTRADOR_INICIAL", "")
        first_name = os.getenv("NOMBRES_ADMINISTRADOR_INICIAL", "Administrador").strip()
        paternal_last_name = (
            os.getenv("APELLIDO_PATERNO_ADMINISTRADOR_INICIAL", "").strip()
            or "Principal"
        )
        maternal_last_name = os.getenv("APELLIDO_MATERNO_ADMINISTRADOR_INICIAL", "").strip()
        username = os.getenv("USUARIO_ADMINISTRADOR_INICIAL", "").lower().strip()
        if not username:
            username = slugify(email.split("@")[0])
        if not valid_gmail(email):
            raise click.ClickException(
                "CORREO_ADMINISTRADOR_INICIAL debe ser una dirección electronica válida"
            )
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,79}", username):
            raise click.ClickException(
                "USUARIO_ADMINISTRADOR_INICIAL debe tener entre 3 y 80 caracteres y usar "
                "solo letras minúsculas, números, punto, guion o guion bajo"
            )
        if not first_name or len(first_name) > 100:
            raise click.ClickException(
                "NOMBRES_ADMINISTRADOR_INICIAL es obligatorio y admite hasta 100 caracteres"
            )
        if not paternal_last_name or len(paternal_last_name) > 100:
            raise click.ClickException(
                "APELLIDO_PATERNO_ADMINISTRADOR_INICIAL es obligatorio y admite hasta 100 caracteres"
            )
        if len(maternal_last_name) > 100:
            raise click.ClickException(
                "APELLIDO_MATERNO_ADMINISTRADOR_INICIAL admite hasta 100 caracteres"
            )
        rules = (
            len(password) >= 10,
            any(char.isupper() for char in password),
            any(char.islower() for char in password),
            any(char.isdigit() for char in password),
            any(not char.isalnum() for char in password),
        )
        if not all(rules):
            raise click.ClickException(
                "CONTRASENA_ADMINISTRADOR_INICIAL debe tener al menos 10 caracteres, una mayúscula, "
                "una minúscula, un número y un carácter especial"
            )
        existing = db.session.scalar(
            select(User).where((User.email == email) | (User.username == username))
        )
        if existing:
            if existing.email == email and existing.username == username:
                click.echo("El administrador inicial ya existe")
                return
            raise click.ClickException(
                "El usuario o correo del administrador inicial ya está registrado"
            )
        user = User(
            username=username,
            email=email,
            role=Role.ADMIN,
            first_name=first_name,
            last_name=paternal_last_name,
            apellido_paterno=paternal_last_name,
            apellido_materno=maternal_last_name or None,
            status=UserStatus.ACTIVE,
            must_change_password=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"ADMIN creado: {user.username} ({user.first_name} {user.last_name})")

    @app.cli.command("cleanup-registration-uploads")
    @with_appcontext
    def cleanup_registration_uploads():
        """Elimina solamente logotipos huérfanos del directorio de solicitudes."""
        from .servicios import (
            audit,
            delete_cloudinary_upload,
            delete_managed_upload,
            managed_upload_path,
        )

        retention_days = app.config["DIAS_RETENCION_SOLICITUDES_RECHAZADAS"]
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        expired_requests = db.session.scalars(
            select(RegistrationRequest).where(
                RegistrationRequest.estado == RegistrationStatus.REJECTED,
                RegistrationRequest.logo_url.is_not(None),
                RegistrationRequest.updated_at <= cutoff,
            )
        ).all()
        expired_removed = 0
        for registration in expired_requests:
            if registration.logo_public_id:
                delete_cloudinary_upload(registration.logo_public_id)
            else:
                delete_managed_upload(registration.logo_url, "solicitudes")
            registration.logo_url = None
            registration.logo_public_id = None
            expired_removed += 1

        referenced = {
            path.resolve()
            for url in db.session.scalars(
                select(RegistrationRequest.logo_url).where(
                    RegistrationRequest.logo_url.is_not(None)
                )
            ).all()
            if (path := managed_upload_path(url, "solicitudes"))
        }
        folder = (Path(app.config["CARPETA_CARGAS"]) / "solicitudes").resolve()
        removed = 0
        if folder.is_dir():
            for path in folder.iterdir():
                if path.is_file() and path.resolve() not in referenced:
                    path.unlink()
                    removed += 1
        click.echo(f"Logotipos huérfanos eliminados: {removed}")

        audit(
            "LIMPIAR_ARCHIVOS_SOLICITUDES",
            "RegistrationRequest",
            after={
                "dias_retencion": retention_days,
                "logos_rechazados_eliminados": expired_removed,
                "archivos_huerfanos_eliminados": removed,
            },
        )
        db.session.commit()
        click.echo(f"Logotipos rechazados vencidos eliminados: {expired_removed}")

    @app.cli.command("seed-productive-sectors")
    @with_appcontext
    def seed_productive_sectors():
        names = [
            "Textiles y Confecciones",
            "Cuero y Calzados",
            "Alimentos y Bebidas Procesados",
            "Madera y Carpintería",
            "Orfebrería y Joyería",
            "Cosmética Natural y Cuidado Personal",
            "Artesanía Tradicional o Decorativa",
            "Otros",
        ]
        for name in names:
            if not db.session.scalar(
                select(ProductiveSector.id).where(ProductiveSector.nombre == name)
            ):
                db.session.add(ProductiveSector(nombre=name, es_otro=name == "Otros"))
        db.session.commit()
        click.echo("Sectores productivos iniciales creados")

    @app.cli.command("seed-catalogs")
    @with_appcontext
    def seed_catalogs():
        for name in [
            "Microempresa",
            "Productor",
            "Artesano",
            "Emprendimiento",
            "Asociación",
            "Cooperativa",
            "Otro",
        ]:
            if not db.session.scalar(
                select(ExhibitorType).where(ExhibitorType.nombre == name)
            ):
                db.session.add(ExhibitorType(nombre=name))
        for name in ["Alimentos", "Artesanías", "Textiles", "Cosmética natural", "Otros"]:
            if not db.session.scalar(select(Category).where(Category.nombre == name)):
                db.session.add(Category(nombre=name, slug=slugify(name)))
        db.session.commit()
        click.echo("Catálogos iniciales creados")
