"""Dominio de solicitudes y unidades productivas con compatibilidad aditiva."""

from alembic import op
import sqlalchemy as sa


revision = "20260721_0002"
down_revision = "20260718_0001"
branch_labels = None
depends_on = None


def _add_enum_value(name, value):
    if op.get_bind().dialect.name == "postgresql":
        # PostgreSQL does not allow a newly-added enum value to be used until
        # the transaction that introduced it has committed.
        with op.get_context().autocommit_block():
            op.execute(f"ALTER TYPE {name} ADD VALUE IF NOT EXISTS '{value}'")


def upgrade():
    for name, values in {
        "rol_usuario": ("ADMIN", "PRODUCTIVE_UNIT_RESPONSIBLE"),
        "estado_usuario": ("BLOCKED",),
        "estado_asignacion": ("INACTIVE",),
        "estado_producto": ("DRAFT", "RETIRED"),
    }.items():
        for value in values:
            _add_enum_value(name, value)

    op.add_column("usuarios", sa.Column("bloqueado_hasta", sa.DateTime(timezone=True)))
    op.add_column("usuarios", sa.Column("version_sesion", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("auditorias", sa.Column("resultado", sa.String(30), nullable=False, server_default="SUCCESS"))

    estado_sector = sa.Enum("ACTIVE", "INACTIVE", name="estado_sector_productivo")
    estado_solicitud = sa.Enum("PENDING", "APPROVED", "REJECTED", name="estado_solicitud_registro")
    estado_notificacion = sa.Enum("PENDING", "SENT", "FAILED", name="estado_notificacion_solicitud")
    estado_unidad = sa.Enum("ACTIVE", "INACTIVE", "SUSPENDED", name="estado_unidad_productiva")
    estado_sector_unidad = sa.Enum("ACTIVE", "INACTIVE", name="estado_sector_unidad")
    estado_participacion = sa.Enum("PENDING", "AUTHORIZED", "REJECTED", "REVOKED", "INACTIVE", name="estado_participacion_feria")

    op.create_table(
        "sectores_productivos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(150), nullable=False),
        sa.Column("descripcion", sa.Text()),
        sa.Column("estado", estado_sector, nullable=False),
        sa.Column("es_otro", sa.Boolean(), nullable=False),
        sa.Column("fecha_eliminacion", sa.DateTime(timezone=True)),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre"),
    )
    op.create_index("indice_sectores_productivos_nombre", "sectores_productivos", ["nombre"])
    op.create_index("indice_sectores_productivos_estado", "sectores_productivos", ["estado"])

    op.create_table(
        "solicitudes_registro",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("nombre_comercial", sa.String(200), nullable=False),
        sa.Column("razon_social", sa.String(200), nullable=False),
        sa.Column("nit", sa.String(50)),
        sa.Column("registro_seprec", sa.String(100)),
        sa.Column("registro_pro_bolivia", sa.String(100)),
        sa.Column("nombre_representante", sa.String(200), nullable=False),
        sa.Column("departamento", sa.String(80), nullable=False),
        sa.Column("direccion_fisica", sa.String(255), nullable=False),
        sa.Column("telefono_whatsapp", sa.String(30), nullable=False),
        sa.Column("correo_electronico", sa.String(255), nullable=False),
        sa.Column("facebook_url", sa.String(500)),
        sa.Column("instagram_url", sa.String(500)),
        sa.Column("tiktok_url", sa.String(500)),
        sa.Column("resena_comercial", sa.Text(), nullable=False),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("estado", estado_solicitud, nullable=False),
        sa.Column("fecha_revision", sa.DateTime(timezone=True)),
        sa.Column("observaciones", sa.Text()),
        sa.Column("motivo_rechazo", sa.Text()),
        sa.Column("reviewed_by", sa.Uuid()),
        sa.Column("credentials_sent_at", sa.DateTime(timezone=True)),
        sa.Column("notification_status", estado_notificacion),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reviewed_by"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("indice_solicitudes_registro_correo_electronico", "solicitudes_registro", ["correo_electronico"])
    op.create_index("indice_solicitudes_registro_estado", "solicitudes_registro", ["estado"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE UNIQUE INDEX solicitud_pendiente_correo_unica ON solicitudes_registro (correo_electronico) WHERE estado = 'PENDING'")
        op.execute("CREATE UNIQUE INDEX solicitud_pendiente_nit_unica ON solicitudes_registro (nit) WHERE estado = 'PENDING' AND nit IS NOT NULL")
    else:
        op.create_index("solicitud_pendiente_correo_unica", "solicitudes_registro", ["correo_electronico"], unique=True)

    op.create_table(
        "sectores_solicitud_registro",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("registration_request_id", sa.Uuid(), nullable=False),
        sa.Column("productive_sector_id", sa.Uuid(), nullable=False),
        sa.Column("detalle_otro", sa.String(255)),
        sa.ForeignKeyConstraint(["registration_request_id"], ["solicitudes_registro.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["productive_sector_id"], ["sectores_productivos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_request_id", "productive_sector_id", name="sector_solicitud_registro_unico"),
    )

    op.create_table(
        "unidades_productivas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("registration_request_id", sa.Uuid(), nullable=False),
        sa.Column("nombre_comercial", sa.String(200), nullable=False),
        sa.Column("razon_social", sa.String(200), nullable=False),
        sa.Column("nit", sa.String(50)),
        sa.Column("registro_seprec", sa.String(100)),
        sa.Column("registro_pro_bolivia", sa.String(100)),
        sa.Column("nombre_representante", sa.String(200), nullable=False),
        sa.Column("departamento", sa.String(80), nullable=False),
        sa.Column("direccion_fisica", sa.String(255), nullable=False),
        sa.Column("telefono_whatsapp", sa.String(30), nullable=False),
        sa.Column("correo_electronico", sa.String(255), nullable=False),
        sa.Column("facebook_url", sa.String(500)),
        sa.Column("instagram_url", sa.String(500)),
        sa.Column("tiktok_url", sa.String(500)),
        sa.Column("resena_comercial", sa.Text(), nullable=False),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("estado", estado_unidad, nullable=False),
        sa.Column("fecha_aprobacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_eliminacion", sa.DateTime(timezone=True)),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["registration_request_id"], ["solicitudes_registro.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"), sa.UniqueConstraint("registration_request_id"),
        sa.UniqueConstraint("nit"), sa.UniqueConstraint("correo_electronico"),
    )
    for column in ("nombre_comercial", "departamento", "correo_electronico", "estado"):
        op.create_index(f"indice_unidades_productivas_{column}", "unidades_productivas", [column])

    op.create_table(
        "sectores_unidad",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("productive_unit_id", sa.Uuid(), nullable=False),
        sa.Column("productive_sector_id", sa.Uuid(), nullable=False),
        sa.Column("detalle_otro", sa.String(255)),
        sa.Column("estado", estado_sector_unidad, nullable=False),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("detalle_otro IS NULL OR length(trim(detalle_otro)) > 0", name="detalle_otro_no_vacio"),
        sa.ForeignKeyConstraint(["productive_unit_id"], ["unidades_productivas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["productive_sector_id"], ["sectores_productivos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("productive_unit_id", "productive_sector_id", name="sector_unidad_unico"),
    )

    op.add_column("productos", sa.Column("unidad_productiva_id", sa.Uuid()))
    for name, type_ in (
        ("nombre_comercial", sa.String(200)), ("descripcion_tecnica", sa.Text()),
        ("materia_prima", sa.Text()), ("dimensiones", sa.String(255)),
        ("colores_disponibles", sa.String(255)), ("certificaciones", sa.Text()),
        ("presentacion_empaque", sa.String(255)), ("precio_referencia", sa.Numeric(10, 2)),
        ("capacidad_produccion_stock", sa.String(255)),
    ):
        op.add_column("productos", sa.Column(name, type_))
    op.create_foreign_key("foranea_productos_unidad_productiva_id_unidades_productivas", "productos", "unidades_productivas", ["unidad_productiva_id"], ["id"])
    op.create_index("indice_productos_unidad_productiva_id", "productos", ["unidad_productiva_id"])
    op.alter_column("productos", "expositor_id", existing_type=sa.Uuid(), nullable=True)
    op.alter_column("productos", "categoria_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("imagenes_producto", sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    op.add_column("ferias", sa.Column("ubicacion", sa.String(255)))
    op.add_column("ferias", sa.Column("fecha_desactivacion", sa.DateTime(timezone=True)))
    op.add_column("ferias", sa.Column("fecha_finalizacion", sa.DateTime(timezone=True)))

    op.create_table(
        "participaciones_feria",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fair_id", sa.Uuid(), nullable=False),
        sa.Column("productive_unit_id", sa.Uuid(), nullable=False),
        sa.Column("estado", estado_participacion, nullable=False),
        sa.Column("observaciones", sa.Text()),
        sa.Column("authorized_by", sa.Uuid()),
        sa.Column("authorized_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["fair_id"], ["ferias.id"]),
        sa.ForeignKeyConstraint(["productive_unit_id"], ["unidades_productivas.id"]),
        sa.ForeignKeyConstraint(["authorized_by"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fair_id", "productive_unit_id", name="participacion_feria_unica"),
    )
    for column in ("fair_id", "productive_unit_id", "estado"):
        op.create_index(f"indice_participaciones_feria_{column}", "participaciones_feria", [column])

    sectors = [
        "Textiles y Confecciones", "Cuero y Calzados", "Alimentos y Bebidas Procesados",
        "Madera y Carpintería", "Orfebrería y Joyería", "Cosmética Natural y Cuidado Personal",
        "Artesanía Tradicional o Decorativa", "Otros",
    ]
    table = sa.table("sectores_productivos", sa.column("id", sa.Uuid()), sa.column("nombre", sa.String()), sa.column("estado", estado_sector), sa.column("es_otro", sa.Boolean()), sa.column("fecha_creacion", sa.DateTime(timezone=True)), sa.column("fecha_actualizacion", sa.DateTime(timezone=True)))
    import uuid
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    op.bulk_insert(table, [{"id": uuid.uuid5(uuid.NAMESPACE_URL, f"catalogo:{name}"), "nombre": name, "estado": "ACTIVE", "es_otro": name == "Otros", "fecha_creacion": now, "fecha_actualizacion": now} for name in sectors])

    # Every legacy exhibitor becomes an approved historical request and a
    # productive unit.  Reusing the UUID in different tables makes the mapping
    # deterministic and lets products/participations be copied without loss.
    if op.get_bind().dialect.name == "postgresql":
        other_sector_id = "239f644c-06b6-5982-8125-0a1df47d8b19"
        op.execute("""
            INSERT INTO solicitudes_registro (
                id, nombre_comercial, razon_social, nit, nombre_representante,
                departamento, direccion_fisica, telefono_whatsapp,
                correo_electronico, resena_comercial, logo_url, estado,
                fecha_revision, notification_status, fecha_creacion, fecha_actualizacion
            )
            SELECT e.id, e.nombre_comercial, e.nombre_comercial,
                   CASE WHEN e.tipo_documento::text = 'NIT' THEN e.numero_documento ELSE NULL END,
                   concat_ws(' ', e.nombre_responsable, e.apellido_responsable,
                             e.apellido_paterno_responsable, e.apellido_materno_responsable),
                   e.departamento, COALESCE(NULLIF(e.direccion, ''), 'No especificada'),
                   e.celular_whatsapp, lower(e.correo),
                   COALESCE(NULLIF(e.descripcion, ''), NULLIF(e.descripcion_productos, ''), 'Sin reseña comercial registrada'),
                   e.logo, 'APPROVED', e.fecha_creacion, 'PENDING',
                   e.fecha_creacion, e.fecha_actualizacion
              FROM expositores e
            ON CONFLICT (id) DO NOTHING
        """)
        op.execute("""
            INSERT INTO unidades_productivas (
                id, user_id, registration_request_id, nombre_comercial,
                razon_social, nit, nombre_representante, departamento,
                direccion_fisica, telefono_whatsapp, correo_electronico,
                resena_comercial, logo_url, estado, fecha_aprobacion,
                fecha_eliminacion, fecha_creacion, fecha_actualizacion
            )
            SELECT e.id, e.usuario_id, e.id, e.nombre_comercial, e.nombre_comercial,
                   CASE WHEN e.tipo_documento::text = 'NIT' THEN e.numero_documento ELSE NULL END,
                   concat_ws(' ', e.nombre_responsable, e.apellido_responsable,
                             e.apellido_paterno_responsable, e.apellido_materno_responsable),
                   e.departamento, COALESCE(NULLIF(e.direccion, ''), 'No especificada'),
                   e.celular_whatsapp, lower(e.correo),
                   COALESCE(NULLIF(e.descripcion, ''), NULLIF(e.descripcion_productos, ''), 'Sin reseña comercial registrada'),
                   e.logo,
                   CASE WHEN e.estado::text = 'ACTIVE' THEN 'ACTIVE'::estado_unidad_productiva
                        WHEN e.estado::text = 'INACTIVE' THEN 'INACTIVE'::estado_unidad_productiva
                        ELSE 'SUSPENDED'::estado_unidad_productiva END,
                   e.fecha_creacion, e.fecha_eliminacion, e.fecha_creacion, e.fecha_actualizacion
              FROM expositores e
            ON CONFLICT (id) DO NOTHING
        """)
        op.execute(f"""
            INSERT INTO sectores_solicitud_registro (
                id, registration_request_id, productive_sector_id, detalle_otro
            )
            SELECT e.id, e.id, '{other_sector_id}',
                   COALESCE(NULLIF(e.nombre_tipo_expositor, ''), 'Migrado desde expositor anterior')
              FROM expositores e
            ON CONFLICT (id) DO NOTHING
        """)
        op.execute(f"""
            INSERT INTO sectores_unidad (
                id, productive_unit_id, productive_sector_id, detalle_otro,
                estado, fecha_creacion, fecha_actualizacion
            )
            SELECT e.id, e.id, '{other_sector_id}',
                   COALESCE(NULLIF(e.nombre_tipo_expositor, ''), 'Migrado desde expositor anterior'),
                   'ACTIVE', e.fecha_creacion, e.fecha_actualizacion
              FROM expositores e
            ON CONFLICT (id) DO NOTHING
        """)
        op.execute("""
            UPDATE productos
               SET unidad_productiva_id = expositor_id,
                   nombre_comercial = nombre,
                   descripcion_tecnica = descripcion,
                   materia_prima = COALESCE(NULLIF(materiales_o_ingredientes, ''), 'No especificada'),
                   presentacion_empaque = COALESCE(NULLIF(presentacion, ''), 'No especificada'),
                   precio_referencia = precio,
                   capacidad_produccion_stock = 'No especificada',
                   estado = CASE WHEN estado::text = 'INACTIVE' THEN 'DRAFT'::estado_producto
                                 WHEN estado::text = 'DELETED' THEN 'RETIRED'::estado_producto
                                 ELSE estado END
             WHERE expositor_id IS NOT NULL
        """)
        op.execute("""
            INSERT INTO participaciones_feria (
                id, fair_id, productive_unit_id, estado, observaciones,
                authorized_by, authorized_at, revoked_at,
                fecha_creacion, fecha_actualizacion
            )
            SELECT a.id, a.feria_id, a.expositor_id,
                   a.estado::text::estado_participacion_feria, a.observaciones,
                   a.autorizado_por_usuario_id, a.fecha_autorizacion,
                   CASE WHEN a.estado::text = 'REVOKED' THEN a.fecha_actualizacion ELSE NULL END,
                   a.fecha_creacion, a.fecha_actualizacion
              FROM expositores_feria a
            ON CONFLICT (id) DO NOTHING
        """)
        op.execute("""
            DO $$
            BEGIN
                IF (SELECT count(*) FROM expositores) <>
                   (SELECT count(*) FROM unidades_productivas u JOIN expositores e ON e.id = u.id) THEN
                    RAISE EXCEPTION 'No se migraron todas las Unidades Productivas';
                END IF;
                IF (SELECT count(*) FROM productos WHERE expositor_id IS NOT NULL) <>
                   (SELECT count(*) FROM productos WHERE expositor_id IS NOT NULL AND unidad_productiva_id IS NOT NULL) THEN
                    RAISE EXCEPTION 'No se migraron todos los productos';
                END IF;
                IF (SELECT count(*) FROM expositores_feria) <>
                   (SELECT count(*) FROM participaciones_feria p JOIN expositores_feria a ON a.id = p.id) THEN
                    RAISE EXCEPTION 'No se migraron todas las participaciones';
                END IF;
            END $$
        """)


def downgrade():
    op.drop_table("participaciones_feria")
    for column in ("fecha_finalizacion", "fecha_desactivacion", "ubicacion"):
        op.drop_column("ferias", column)
    op.drop_column("imagenes_producto", "fecha_actualizacion")
    op.drop_constraint("foranea_productos_unidad_productiva_id_unidades_productivas", "productos", type_="foreignkey")
    for column in ("capacidad_produccion_stock", "precio_referencia", "presentacion_empaque", "certificaciones", "colores_disponibles", "dimensiones", "materia_prima", "descripcion_tecnica", "nombre_comercial", "unidad_productiva_id"):
        op.drop_column("productos", column)
    op.drop_table("sectores_unidad")
    op.drop_table("unidades_productivas")
    op.drop_table("sectores_solicitud_registro")
    op.drop_table("solicitudes_registro")
    op.drop_table("sectores_productivos")
    op.drop_column("usuarios", "version_sesion")
    op.drop_column("usuarios", "bloqueado_hasta")
    op.drop_column("auditorias", "resultado")
