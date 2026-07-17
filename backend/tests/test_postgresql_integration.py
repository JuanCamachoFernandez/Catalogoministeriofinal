import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app import create_app
from app.config import Config
from app.extensions import db


@pytest.mark.postgres
def test_postgresql_test_database_connects():
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
        assert db.session.scalar(text("select 1")) == 1
