"""Unificar roles canonicos

Revision ID: 43b2b84f6f42
Revises: 8eb86b9491a1
Create Date: 2026-07-31 12:20:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "43b2b84f6f42"
down_revision = "8eb86b9491a1"
branch_labels = None
depends_on = None

OLD_ROLE_ENUM = sa.Enum(
    "SUPERADMIN",
    "ADMIN_VICEMINISTERIO",
    "EXPOSITOR",
    "ADMIN",
    "PRODUCTIVE_UNIT_RESPONSIBLE",
    name="rol_usuario",
)
NEW_ROLE_ENUM = sa.Enum(
    "ADMIN",
    "PRODUCTIVE_UNIT_RESPONSIBLE",
    name="rol_usuario",
)


def _normalize_role_data():
    op.execute(
        sa.text(
            """
            UPDATE usuarios
            SET rol = CASE
                WHEN rol IN ('SUPERADMIN', 'ADMIN_VICEMINISTERIO', 'ADMIN') THEN 'ADMIN'
                WHEN rol IN ('EXPOSITOR', 'PRODUCTIVE_UNIT_RESPONSIBLE') THEN 'PRODUCTIVE_UNIT_RESPONSIBLE'
                ELSE rol
            END
            """
        )
    )


def _upgrade_postgresql():
    _normalize_role_data()
    op.execute("ALTER TYPE rol_usuario RENAME TO rol_usuario_old")
    NEW_ROLE_ENUM.create(op.get_bind(), checkfirst=False)
    op.execute(
        """
        ALTER TABLE usuarios
        ALTER COLUMN rol TYPE rol_usuario
        USING rol::text::rol_usuario
        """
    )
    op.execute("DROP TYPE rol_usuario_old")


def _downgrade_postgresql():
    op.execute("ALTER TYPE rol_usuario RENAME TO rol_usuario_new")
    OLD_ROLE_ENUM.create(op.get_bind(), checkfirst=False)
    op.execute(
        """
        ALTER TABLE usuarios
        ALTER COLUMN rol TYPE rol_usuario
        USING rol::text::rol_usuario
        """
    )
    op.execute("DROP TYPE rol_usuario_new")


def _upgrade_sqlite():
    _normalize_role_data()
    with op.batch_alter_table("usuarios", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "rol",
            existing_type=OLD_ROLE_ENUM,
            type_=NEW_ROLE_ENUM,
            existing_nullable=False,
        )


def _downgrade_sqlite():
    with op.batch_alter_table("usuarios", schema=None, recreate="always") as batch_op:
        batch_op.alter_column(
            "rol",
            existing_type=NEW_ROLE_ENUM,
            type_=OLD_ROLE_ENUM,
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
