import os

import pytest
from alembic.migration import MigrationContext
from flask_migrate import upgrade
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from app import create_app
from app.configuracion import Config
from app.extensiones import db


@pytest.mark.postgres
def test_postgresql_migrations_run_from_zero():
    database_url = os.getenv("DIRECCION_BASE_DATOS_PRUEBAS")
    if not database_url:
        pytest.skip("DIRECCION_BASE_DATOS_PRUEBAS no configurada")
    database_name = make_url(database_url).database or ""
    if not database_name.endswith("_test"):
        pytest.fail("DIRECCION_BASE_DATOS_PRUEBAS debe apuntar a una base terminada en _test")

    class PostgreSQLTestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = database_url

    app = create_app(PostgreSQLTestConfig)
    with app.app_context():
        db.session.execute(text("DROP SCHEMA public CASCADE"))
        db.session.execute(text("CREATE SCHEMA public"))
        db.session.commit()
        upgrade()

        tables = set(inspect(db.engine).get_table_names())
        assert {
            "auditorias",
            "categorias",
            "codigos_acceso_revocados",
            "estados_memoria_temporal",
            "expositores",
            "expositores_feria",
            "alembic_version",
            "ferias",
            "imagenes_feria",
            "imagenes_producto",
            "perfiles_administradores",
            "productos",
            "sectores_productivos",
            "solicitudes_registro",
            "sectores_solicitud_registro",
            "unidades_productivas",
            "sectores_unidad",
            "participaciones_feria",
            "recuperaciones_contrasena",
            "tipos_expositor",
            "tipos_expositor_asignados",
            "unidades_administrativas",
            "usuarios",
        } <= tables
        assert {
            "users",
            "exhibitors",
            "fairs",
            "products",
            "categories",
            "audits",
        }.isdisjoint(tables)
        with db.engine.connect() as connection:
            revision = MigrationContext.configure(connection).get_current_revision()
        assert revision == "b1c3a5d7e9f0"

        image_indexes = {item["name"] for item in inspect(db.engine).get_indexes("imagenes_producto")}
        assert "indice_imagenes_producto_producto_id" in image_indexes
        assert "imagen_producto_portada_unica" in image_indexes
        image_constraints = {
            item["name"] for item in inspect(db.engine).get_unique_constraints("imagenes_producto")
        }
        assert "imagen_producto_orden_unico" in image_constraints
