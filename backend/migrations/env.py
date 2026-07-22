from alembic import context
from flask import current_app

config = context.config
config.set_main_option(
    "sqlalchemy.url",
    str(current_app.extensions["migrate"].db.engine.url).replace("%", "%%"),
)
target_metadata = current_app.extensions["migrate"].db.metadata


def include_managed_objects(_object, _name, object_type, reflected, compare_to):
    """No propone borrar tablas ajenas o legadas que la aplicación no administra."""
    return not (object_type == "table" and reflected and compare_to is None)


def run_migrations_offline():
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        version_table="version_migraciones",
        include_object=include_managed_objects,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    with current_app.extensions["migrate"].db.engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            version_table="version_migraciones",
            include_object=include_managed_objects,
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
