"""Cleanup estados residuales

Revision ID: b1c3a5d7e9f0
Revises: 43b2b84f6f42
Create Date: 2026-07-31 18:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b1c3a5d7e9f0"
down_revision = "43b2b84f6f42"
branch_labels = None
depends_on = None

OLD_UNIT_STATUS_ENUM = sa.Enum(
    "ACTIVE",
    "INACTIVE",
    "SUSPENDED",
    name="estado_unidad_productiva",
)
NEW_UNIT_STATUS_ENUM = sa.Enum(
    "ACTIVE",
    "INACTIVE",
    name="estado_unidad_productiva",
)

OLD_PRODUCT_STATUS_ENUM = sa.Enum(
    "DRAFT",
    "AVAILABLE",
    "OUT_OF_STOCK",
    "RETIRED",
    "INACTIVE",
    "DELETED",
    name="estado_producto",
)
NEW_PRODUCT_STATUS_ENUM = sa.Enum(
    "DRAFT",
    "AVAILABLE",
    "OUT_OF_STOCK",
    "RETIRED",
    "DELETED",
    name="estado_producto",
)

OLD_ASSIGNMENT_STATUS_ENUM = sa.Enum(
    "PENDING",
    "AUTHORIZED",
    "REJECTED",
    "REVOKED",
    "INACTIVE",
    name="estado_asignacion",
)
NEW_ASSIGNMENT_STATUS_ENUM = sa.Enum(
    "PENDING",
    "AUTHORIZED",
    "REVOKED",
    "INACTIVE",
    name="estado_asignacion",
)

OLD_PARTICIPATION_STATUS_ENUM = sa.Enum(
    "PENDING",
    "AUTHORIZED",
    "REJECTED",
    "REVOKED",
    "INACTIVE",
    name="estado_participacion_feria",
)
NEW_PARTICIPATION_STATUS_ENUM = sa.Enum(
    "PENDING",
    "AUTHORIZED",
    "REVOKED",
    "INACTIVE",
    name="estado_participacion_feria",
)


def _normalize_data():
    op.execute(
        sa.text(
            """
            UPDATE unidades_productivas
            SET estado = 'INACTIVE'
            WHERE estado = 'SUSPENDED'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE productos
            SET estado = 'RETIRED'
            WHERE estado = 'INACTIVE'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE expositores_feria
            SET estado = 'REVOKED'
            WHERE estado = 'REJECTED'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE participaciones_feria
            SET estado = 'REVOKED'
            WHERE estado = 'REJECTED'
            """
        )
    )


def _alter_postgresql_enum(table_name, enum_name, new_enum, column_name="estado"):
    op.execute(f"ALTER TYPE {enum_name} RENAME TO {enum_name}_old")
    new_enum.create(op.get_bind(), checkfirst=False)
    op.execute(
        f"""
        ALTER TABLE {table_name}
        ALTER COLUMN {column_name} TYPE {enum_name}
        USING {column_name}::text::{enum_name}
        """
    )
    op.execute(f"DROP TYPE {enum_name}_old")


def _upgrade_postgresql():
    _normalize_data()
    _alter_postgresql_enum(
        "unidades_productivas",
        "estado_unidad_productiva",
        NEW_UNIT_STATUS_ENUM,
    )
    _alter_postgresql_enum("productos", "estado_producto", NEW_PRODUCT_STATUS_ENUM)
    _alter_postgresql_enum(
        "expositores_feria",
        "estado_asignacion",
        NEW_ASSIGNMENT_STATUS_ENUM,
    )
    _alter_postgresql_enum(
        "participaciones_feria",
        "estado_participacion_feria",
        NEW_PARTICIPATION_STATUS_ENUM,
    )


def _downgrade_postgresql():
    op.execute("ALTER TYPE estado_unidad_productiva RENAME TO estado_unidad_productiva_new")
    OLD_UNIT_STATUS_ENUM.create(op.get_bind(), checkfirst=False)
    op.execute(
        """
        ALTER TABLE unidades_productivas
        ALTER COLUMN estado TYPE estado_unidad_productiva
        USING estado::text::estado_unidad_productiva
        """
    )
    op.execute("DROP TYPE estado_unidad_productiva_new")

    op.execute("ALTER TYPE estado_producto RENAME TO estado_producto_new")
    OLD_PRODUCT_STATUS_ENUM.create(op.get_bind(), checkfirst=False)
    op.execute(
        """
        ALTER TABLE productos
        ALTER COLUMN estado TYPE estado_producto
        USING estado::text::estado_producto
        """
    )
    op.execute("DROP TYPE estado_producto_new")

    op.execute("ALTER TYPE estado_asignacion RENAME TO estado_asignacion_new")
    OLD_ASSIGNMENT_STATUS_ENUM.create(op.get_bind(), checkfirst=False)
    op.execute(
        """
        ALTER TABLE expositores_feria
        ALTER COLUMN estado TYPE estado_asignacion
        USING estado::text::estado_asignacion
        """
    )
    op.execute("DROP TYPE estado_asignacion_new")

    op.execute("ALTER TYPE estado_participacion_feria RENAME TO estado_participacion_feria_new")
    OLD_PARTICIPATION_STATUS_ENUM.create(op.get_bind(), checkfirst=False)
    op.execute(
        """
        ALTER TABLE participaciones_feria
        ALTER COLUMN estado TYPE estado_participacion_feria
        USING estado::text::estado_participacion_feria
        """
    )
    op.execute("DROP TYPE estado_participacion_feria_new")


def _upgrade_sqlite():
    _normalize_data()
    with op.batch_alter_table("unidades_productivas", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "estado",
            existing_type=OLD_UNIT_STATUS_ENUM,
            type_=NEW_UNIT_STATUS_ENUM,
            existing_nullable=False,
        )
    with op.batch_alter_table("productos", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "estado",
            existing_type=OLD_PRODUCT_STATUS_ENUM,
            type_=NEW_PRODUCT_STATUS_ENUM,
            existing_nullable=False,
        )
    with op.batch_alter_table("expositores_feria", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "estado",
            existing_type=OLD_ASSIGNMENT_STATUS_ENUM,
            type_=NEW_ASSIGNMENT_STATUS_ENUM,
            existing_nullable=False,
        )
    with op.batch_alter_table("participaciones_feria", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "estado",
            existing_type=OLD_PARTICIPATION_STATUS_ENUM,
            type_=NEW_PARTICIPATION_STATUS_ENUM,
            existing_nullable=False,
        )


def _downgrade_sqlite():
    with op.batch_alter_table("unidades_productivas", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "estado",
            existing_type=NEW_UNIT_STATUS_ENUM,
            type_=OLD_UNIT_STATUS_ENUM,
            existing_nullable=False,
        )
    with op.batch_alter_table("productos", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "estado",
            existing_type=NEW_PRODUCT_STATUS_ENUM,
            type_=OLD_PRODUCT_STATUS_ENUM,
            existing_nullable=False,
        )
    with op.batch_alter_table("expositores_feria", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "estado",
            existing_type=NEW_ASSIGNMENT_STATUS_ENUM,
            type_=OLD_ASSIGNMENT_STATUS_ENUM,
            existing_nullable=False,
        )
    with op.batch_alter_table("participaciones_feria", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "estado",
            existing_type=NEW_PARTICIPATION_STATUS_ENUM,
            type_=OLD_PARTICIPATION_STATUS_ENUM,
            existing_nullable=False,
        )


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _upgrade_postgresql()
        return
    _upgrade_sqlite()


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        _downgrade_postgresql()
        return
    _downgrade_sqlite()
