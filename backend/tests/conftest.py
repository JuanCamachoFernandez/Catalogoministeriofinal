import os
os.environ.setdefault("DIRECCION_BASE_DATOS", "sqlite+pysqlite:///:memory:")
import pytest
from app import create_app
from app.configuracion import Config
from app.extensiones import db

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
        # PostgreSQL cannot drop tables while the scoped session still owns an
        # idle transaction (for example after reading the public cache version).
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):return app.test_client()
