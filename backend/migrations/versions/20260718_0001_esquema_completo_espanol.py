"""Esquema inicial completo con nombres fisicos en espanol."""

from alembic import op
import sqlalchemy as sa


revision = "20260718_0001"
down_revision = None
branch_labels = None
depends_on = None


CONVENCION_NOMBRES = {
    "ix": "indice_%(table_name)s_%(column_0_name)s",
    "uq": "unico_%(table_name)s_%(column_0_name)s",
    "ck": "verificacion_%(table_name)s_%(constraint_name)s",
    "fk": "foranea_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "primaria_%(table_name)s",
}

metadata = sa.MetaData(naming_convention=CONVENCION_NOMBRES)

rol_usuario = sa.Enum(
    "SUPERADMIN", "ADMIN_VICEMINISTERIO", "EXPOSITOR", name="rol_usuario"
)
estado_usuario = sa.Enum("ACTIVE", "INACTIVE", "LOCKED", name="estado_usuario")
tipo_documento = sa.Enum("CI", "NIT", "OTRO", name="tipo_documento")
estado_expositor = sa.Enum("ACTIVE", "INACTIVE", "LOCKED", name="estado_expositor")
estado_feria = sa.Enum(
    "DRAFT", "PUBLISHED", "DISABLED", "FINISHED", name="estado_feria"
)
estado_asignacion = sa.Enum(
    "PENDING", "AUTHORIZED", "REJECTED", "REVOKED", name="estado_asignacion"
)
estado_producto = sa.Enum(
    "AVAILABLE", "OUT_OF_STOCK", "INACTIVE", "DELETED", name="estado_producto"
)

usuarios = sa.Table(
    "usuarios",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("usuario", sa.String(80), nullable=False),
    sa.Column("correo", sa.String(255), nullable=False),
    sa.Column("contrasena_cifrada", sa.Text(), nullable=False),
    sa.Column("rol", rol_usuario, nullable=False),
    sa.Column("nombres", sa.String(100), nullable=False),
    sa.Column("apellidos", sa.String(100), nullable=False),
    sa.Column("apellido_paterno", sa.String(100)),
    sa.Column("apellido_materno", sa.String(100)),
    sa.Column("celular", sa.String(15)),
    sa.Column("foto_perfil", sa.String(500)),
    sa.Column("estado", estado_usuario, nullable=False),
    sa.Column("debe_cambiar_contrasena", sa.Boolean(), nullable=False),
    sa.Column("intentos_fallidos_acceso", sa.Integer(), nullable=False),
    sa.Column("fecha_ultimo_acceso", sa.DateTime(timezone=True)),
    sa.Column("fecha_cambio_contrasena", sa.DateTime(timezone=True)),
    sa.Column("fecha_eliminacion", sa.DateTime(timezone=True)),
    sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
    sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("id"),
)
sa.Index("indice_usuarios_usuario", usuarios.c.usuario, unique=True)
sa.Index("indice_usuarios_correo", usuarios.c.correo, unique=True)

perfiles_administradores = sa.Table(
    "perfiles_administradores",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("usuario_id", sa.Uuid(), nullable=False),
    sa.Column("numero_documento", sa.String(50)),
    sa.Column("cargo", sa.String(150)),
    sa.Column("unidad", sa.String(150)),
    sa.Column("observaciones", sa.Text()),
    sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("usuario_id"),
    sa.UniqueConstraint("numero_documento"),
)

unidades_administrativas = sa.Table(
    "unidades_administrativas",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("nombre", sa.String(150), nullable=False),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("nombre"),
)

recuperaciones_contrasena = sa.Table(
    "recuperaciones_contrasena",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("usuario_id", sa.Uuid(), nullable=False),
    sa.Column("codigo_cifrado", sa.String(64), nullable=False),
    sa.Column("fecha_expiracion", sa.DateTime(timezone=True), nullable=False),
    sa.Column("fecha_verificacion", sa.DateTime(timezone=True)),
    sa.Column("intentos_fallidos", sa.Integer(), nullable=False),
    sa.Column("fecha_uso", sa.DateTime(timezone=True)),
    sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("codigo_cifrado"),
)
sa.Index(
    "indice_recuperaciones_contrasena_usuario_id",
    recuperaciones_contrasena.c.usuario_id,
)

codigos_acceso_revocados = sa.Table(
    "codigos_acceso_revocados",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("identificador_codigo_acceso", sa.String(36), nullable=False),
    sa.Column("fecha_expiracion", sa.DateTime(timezone=True), nullable=False),
    sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("id"),
)
sa.Index(
    "indice_codigos_acceso_revocados_identificador_codigo_acceso",
    codigos_acceso_revocados.c.identificador_codigo_acceso,
    unique=True,
)

tipos_expositor = sa.Table(
    "tipos_expositor",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("nombre", sa.String(80), nullable=False),
    sa.Column("estado", sa.Boolean(), nullable=False),
    sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
    sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("nombre"),
)

expositores = sa.Table(
    "expositores",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("usuario_id", sa.Uuid(), nullable=False),
    sa.Column("nombre_comercial", sa.String(200), nullable=False),
    sa.Column("tipo_documento", tipo_documento, nullable=False),
    sa.Column("numero_documento", sa.String(50), nullable=False),
    sa.Column("nombre_responsable", sa.String(100), nullable=False),
    sa.Column("apellido_responsable", sa.String(100), nullable=False),
    sa.Column("apellido_paterno_responsable", sa.String(100)),
    sa.Column("apellido_materno_responsable", sa.String(100)),
    sa.Column("celular_whatsapp", sa.String(11), nullable=False),
    sa.Column("correo", sa.String(255), nullable=False),
    sa.Column("departamento", sa.String(80), nullable=False),
    sa.Column("municipio", sa.String(100), nullable=False),
    sa.Column("direccion", sa.String(255)),
    sa.Column("descripcion", sa.Text()),
    sa.Column("descripcion_productos", sa.Text()),
    sa.Column("nombre_tipo_expositor", sa.String(200)),
    sa.Column("logo", sa.String(500)),
    sa.Column("estado", estado_expositor, nullable=False),
    sa.Column("fecha_eliminacion", sa.DateTime(timezone=True)),
    sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
    sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("usuario_id"),
    sa.UniqueConstraint("numero_documento"),
    sa.UniqueConstraint("correo"),
)
sa.Index("indice_expositores_nombre_comercial", expositores.c.nombre_comercial)
sa.Index("indice_expositores_departamento", expositores.c.departamento)
sa.Index("indice_expositores_municipio", expositores.c.municipio)

tipos_expositor_asignados = sa.Table(
    "tipos_expositor_asignados",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("expositor_id", sa.Uuid(), nullable=False),
    sa.Column("tipo_expositor_id", sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(
        ["expositor_id"], ["expositores.id"], ondelete="CASCADE"
    ),
    sa.ForeignKeyConstraint(["tipo_expositor_id"], ["tipos_expositor.id"]),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint(
        "expositor_id",
        "tipo_expositor_id",
        name="tipo_expositor_asignado_unico",
    ),
)

ferias = sa.Table(
    "ferias",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("nombre", sa.String(200), nullable=False),
    sa.Column("identificador_url", sa.String(220), nullable=False),
    sa.Column("descripcion", sa.Text()),
    sa.Column("lugar", sa.String(200), nullable=False),
    sa.Column("direccion", sa.String(255)),
    sa.Column("departamento", sa.String(80), nullable=False),
    sa.Column("municipio", sa.String(100), nullable=False),
    sa.Column("fecha_inicio", sa.Date(), nullable=False),
    sa.Column("fecha_fin", sa.Date(), nullable=False),
    sa.Column("hora_inicio", sa.Time()),
    sa.Column("hora_fin", sa.Time()),
    sa.Column("fecha_limite_registro", sa.Date()),
    sa.Column("imagen_portada", sa.String(500)),
    sa.Column("observaciones", sa.Text()),
    sa.Column("estado", estado_feria, nullable=False),
    sa.Column("visible_publicamente", sa.Boolean(), nullable=False),
    sa.Column("creado_por_usuario_id", sa.Uuid(), nullable=False),
    sa.Column("fecha_eliminacion", sa.DateTime(timezone=True)),
    sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
    sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("fecha_fin >= fecha_inicio", name="fechas_validas"),
    sa.ForeignKeyConstraint(["creado_por_usuario_id"], ["usuarios.id"]),
    sa.PrimaryKeyConstraint("id"),
)
sa.Index("indice_ferias_nombre", ferias.c.nombre)
sa.Index("indice_ferias_identificador_url", ferias.c.identificador_url, unique=True)
sa.Index("indice_ferias_departamento", ferias.c.departamento)

imagenes_feria = sa.Table(
    "imagenes_feria",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("feria_id", sa.Uuid(), nullable=False),
    sa.Column("nombre_archivo", sa.String(255), nullable=False),
    sa.Column("direccion_url", sa.String(500), nullable=False),
    sa.Column("texto_alternativo", sa.String(255)),
    sa.Column("es_portada", sa.Boolean()),
    sa.Column("orden_visualizacion", sa.Integer()),
    sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["feria_id"], ["ferias.id"], ondelete="CASCADE"),
    sa.PrimaryKeyConstraint("id"),
)

expositores_feria = sa.Table(
    "expositores_feria",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("feria_id", sa.Uuid(), nullable=False),
    sa.Column("expositor_id", sa.Uuid(), nullable=False),
    sa.Column("estado", estado_asignacion, nullable=False),
    sa.Column("numero_stand", sa.String(40)),
    sa.Column("sector", sa.String(100)),
    sa.Column("observaciones", sa.Text()),
    sa.Column("autorizado_por_usuario_id", sa.Uuid()),
    sa.Column("fecha_autorizacion", sa.DateTime(timezone=True)),
    sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
    sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["feria_id"], ["ferias.id"]),
    sa.ForeignKeyConstraint(["expositor_id"], ["expositores.id"]),
    sa.ForeignKeyConstraint(["autorizado_por_usuario_id"], ["usuarios.id"]),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("feria_id", "expositor_id", name="expositor_feria_unico"),
)

categorias = sa.Table(
    "categorias",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("nombre", sa.String(120), nullable=False),
    sa.Column("identificador_url", sa.String(140), nullable=False),
    sa.Column("descripcion", sa.Text()),
    sa.Column("estado", sa.Boolean(), nullable=False),
    sa.Column("fecha_eliminacion", sa.DateTime(timezone=True)),
    sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
    sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint("nombre"),
    sa.UniqueConstraint("identificador_url"),
)

productos = sa.Table(
    "productos",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("expositor_id", sa.Uuid(), nullable=False),
    sa.Column("categoria_id", sa.Uuid(), nullable=False),
    sa.Column("nombre", sa.String(200), nullable=False),
    sa.Column("identificador_url", sa.String(220), nullable=False),
    sa.Column("descripcion", sa.Text(), nullable=False),
    sa.Column("materiales_o_ingredientes", sa.Text()),
    sa.Column("lugar_origen", sa.String(150)),
    sa.Column("presentacion", sa.String(150)),
    sa.Column("informacion_adicional", sa.Text()),
    sa.Column("precio", sa.Numeric(10, 2)),
    sa.Column("estado", estado_producto, nullable=False),
    sa.Column("destacado", sa.Boolean(), nullable=False),
    sa.Column("fecha_eliminacion", sa.DateTime(timezone=True)),
    sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
    sa.Column("fecha_actualizacion", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["expositor_id"], ["expositores.id"]),
    sa.ForeignKeyConstraint(["categoria_id"], ["categorias.id"]),
    sa.PrimaryKeyConstraint("id"),
    sa.UniqueConstraint(
        "expositor_id",
        "identificador_url",
        name="producto_expositor_url_unico",
    ),
)
sa.Index("indice_productos_expositor_id", productos.c.expositor_id)
sa.Index("indice_productos_categoria_id", productos.c.categoria_id)

imagenes_producto = sa.Table(
    "imagenes_producto",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("producto_id", sa.Uuid(), nullable=False),
    sa.Column("nombre_archivo", sa.String(255), nullable=False),
    sa.Column("direccion_url", sa.String(500), nullable=False),
    sa.Column("texto_alternativo", sa.String(255)),
    sa.Column("es_portada", sa.Boolean()),
    sa.Column("orden_visualizacion", sa.Integer()),
    sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(
        ["producto_id"], ["productos.id"], ondelete="CASCADE"
    ),
    sa.PrimaryKeyConstraint("id"),
)

auditorias = sa.Table(
    "auditorias",
    metadata,
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("usuario_id", sa.Uuid()),
    sa.Column("accion", sa.String(100), nullable=False),
    sa.Column("entidad", sa.String(100), nullable=False),
    sa.Column("entidad_id", sa.Uuid()),
    sa.Column("descripcion", sa.Text(), nullable=False),
    sa.Column("datos_anteriores", sa.JSON()),
    sa.Column("datos_nuevos", sa.JSON()),
    sa.Column("direccion_ip", sa.String(45)),
    sa.Column("agente_usuario", sa.String(500)),
    sa.Column("fecha_creacion", sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
    sa.PrimaryKeyConstraint("id"),
)
sa.Index("indice_auditorias_usuario_id", auditorias.c.usuario_id)
sa.Index("indice_auditorias_accion", auditorias.c.accion)
sa.Index("indice_auditorias_fecha_creacion", auditorias.c.fecha_creacion)

estados_memoria_temporal = sa.Table(
    "estados_memoria_temporal",
    metadata,
    sa.Column("clave", sa.String(80), nullable=False),
    sa.Column("version", sa.BigInteger(), nullable=False),
    sa.PrimaryKeyConstraint("clave"),
)


def upgrade():
    metadata.create_all(bind=op.get_bind(), checkfirst=False)
    op.bulk_insert(
        estados_memoria_temporal,
        [{"clave": "catalogo_publico", "version": 0}],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE version_migraciones "
            "RENAME CONSTRAINT version_migraciones_pkc "
            "TO primaria_version_migraciones"
        )


def downgrade():
    metadata.drop_all(bind=op.get_bind(), checkfirst=False)
