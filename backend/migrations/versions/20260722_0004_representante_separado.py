"""Separa los nombres y apellidos del representante de la unidad productiva."""

from alembic import op
import sqlalchemy as sa


revision = "20260722_0004"
down_revision = "20260721_0003"
branch_labels = None
depends_on = None


def _legacy_parts(full_name):
    parts = (full_name or "").split()
    if len(parts) >= 3:
        return " ".join(parts[:-2]), parts[-2], parts[-1]
    if len(parts) == 2:
        return parts[0], parts[1], ""
    if parts:
        return parts[0], "", ""
    return "", "", ""


def _parts(full_name, names=None, paternal=None, maternal=None):
    if names:
        values = names.strip(), (paternal or "").strip(), (maternal or "").strip()
    else:
        values = _legacy_parts(full_name)
    return tuple(value[:100] for value in values)


def _add_columns(table_name):
    with op.batch_alter_table(table_name) as batch:
        batch.add_column(sa.Column("nombres_representante", sa.String(100)))
        batch.add_column(sa.Column("apellido_paterno_representante", sa.String(100)))
        batch.add_column(sa.Column("apellido_materno_representante", sa.String(100)))


def _make_columns_required_and_drop_legacy(table_name):
    with op.batch_alter_table(table_name) as batch:
        batch.alter_column(
            "nombres_representante", existing_type=sa.String(100), nullable=False
        )
        batch.alter_column(
            "apellido_paterno_representante",
            existing_type=sa.String(100),
            nullable=False,
        )
        batch.alter_column(
            "apellido_materno_representante",
            existing_type=sa.String(100),
            nullable=False,
        )
        batch.drop_column("nombre_representante")


def upgrade():
    _add_columns("solicitudes_registro")
    _add_columns("unidades_productivas")

    solicitudes = sa.table(
        "solicitudes_registro",
        sa.column("id", sa.Uuid()),
        sa.column("nombre_representante", sa.String(200)),
        sa.column("nombres_representante", sa.String(100)),
        sa.column("apellido_paterno_representante", sa.String(100)),
        sa.column("apellido_materno_representante", sa.String(100)),
    )
    unidades = sa.table(
        "unidades_productivas",
        sa.column("id", sa.Uuid()),
        sa.column("user_id", sa.Uuid()),
        sa.column("registration_request_id", sa.Uuid()),
        sa.column("nombre_representante", sa.String(200)),
        sa.column("nombres_representante", sa.String(100)),
        sa.column("apellido_paterno_representante", sa.String(100)),
        sa.column("apellido_materno_representante", sa.String(100)),
    )
    usuarios = sa.table(
        "usuarios",
        sa.column("id", sa.Uuid()),
        sa.column("nombres", sa.String(100)),
        sa.column("apellido_paterno", sa.String(100)),
        sa.column("apellido_materno", sa.String(100)),
    )
    bind = op.get_bind()

    unit_rows = bind.execute(
        sa.select(
            unidades.c.id,
            unidades.c.nombre_representante,
            usuarios.c.nombres,
            usuarios.c.apellido_paterno,
            usuarios.c.apellido_materno,
        ).select_from(unidades.outerjoin(usuarios, usuarios.c.id == unidades.c.user_id))
    ).mappings()
    for row in unit_rows:
        names, paternal, maternal = _parts(
            row["nombre_representante"],
            row["nombres"],
            row["apellido_paterno"],
            row["apellido_materno"],
        )
        bind.execute(
            unidades.update()
            .where(unidades.c.id == row["id"])
            .values(
                nombres_representante=names,
                apellido_paterno_representante=paternal,
                apellido_materno_representante=maternal,
            )
        )

    request_rows = bind.execute(
        sa.select(
            solicitudes.c.id,
            solicitudes.c.nombre_representante,
            usuarios.c.nombres,
            usuarios.c.apellido_paterno,
            usuarios.c.apellido_materno,
        ).select_from(
            solicitudes.outerjoin(
                unidades,
                unidades.c.registration_request_id == solicitudes.c.id,
            ).outerjoin(usuarios, usuarios.c.id == unidades.c.user_id)
        )
    ).mappings()
    for row in request_rows:
        names, paternal, maternal = _parts(
            row["nombre_representante"],
            row["nombres"],
            row["apellido_paterno"],
            row["apellido_materno"],
        )
        bind.execute(
            solicitudes.update()
            .where(solicitudes.c.id == row["id"])
            .values(
                nombres_representante=names,
                apellido_paterno_representante=paternal,
                apellido_materno_representante=maternal,
            )
        )

    _make_columns_required_and_drop_legacy("solicitudes_registro")
    _make_columns_required_and_drop_legacy("unidades_productivas")


def _restore_legacy_column(table_name):
    with op.batch_alter_table(table_name) as batch:
        batch.add_column(sa.Column("nombre_representante", sa.String(200)))

    table = sa.table(
        table_name,
        sa.column("id", sa.Uuid()),
        sa.column("nombre_representante", sa.String(200)),
        sa.column("nombres_representante", sa.String(100)),
        sa.column("apellido_paterno_representante", sa.String(100)),
        sa.column("apellido_materno_representante", sa.String(100)),
    )
    bind = op.get_bind()
    for row in bind.execute(sa.select(table)).mappings():
        full_name = " ".join(
            filter(
                None,
                (
                    row["nombres_representante"],
                    row["apellido_paterno_representante"],
                    row["apellido_materno_representante"],
                ),
            )
        )
        bind.execute(
            table.update()
            .where(table.c.id == row["id"])
            .values(nombre_representante=full_name)
        )

    with op.batch_alter_table(table_name) as batch:
        batch.alter_column(
            "nombre_representante", existing_type=sa.String(200), nullable=False
        )
        batch.drop_column("apellido_materno_representante")
        batch.drop_column("apellido_paterno_representante")
        batch.drop_column("nombres_representante")


def downgrade():
    _restore_legacy_column("unidades_productivas")
    _restore_legacy_column("solicitudes_registro")
