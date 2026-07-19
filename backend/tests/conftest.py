import os
os.environ.setdefault("DIRECCION_BASE_DATOS", "sqlite+pysqlite:///:memory:")
import pytest
from app import create_app
from app.config import Config
from app.extensions import db

class TestConfig(Config):
    TESTING=True
    SQLALCHEMY_DATABASE_URI=os.getenv(
        "DIRECCION_BASE_DATOS_PRUEBAS", "sqlite+pysqlite:///:memory:"
    )

@pytest.fixture
def app(tmp_path):
    TestConfig.CARPETA_CARGAS = str(tmp_path / "uploads")
    app=create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):return app.test_client()
