import os

import pytest
from alembic.migration import MigrationContext
from flask_migrate import upgrade
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from app import create_app
from app.config import Config
from app.extensions import db


@pytest.mark.postgres
def test_postgresql_migrations_run_from_zero():
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL no configurada")
    database_name = make_url(database_url).database or ""
    if not database_name.endswith("_test"):
        pytest.fail("TEST_DATABASE_URL debe apuntar a una base terminada en _test")

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
            "alembic_version",
            "users",
            "fairs",
            "fair_exhibitors",
            "products",
            "revoked_tokens",
            "cache_states",
        } <= tables
        with db.engine.connect() as connection:
            revision = MigrationContext.configure(connection).get_current_revision()
        assert revision == "d742fe19a603"
