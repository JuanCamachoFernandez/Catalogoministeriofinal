import os
os.environ.setdefault("DATABASE_URL","sqlite+pysqlite:///:memory:")
import pytest
from app import create_app
from app.config import Config
from app.extensions import db

class TestConfig(Config):
    TESTING=True
    SQLALCHEMY_DATABASE_URI="sqlite+pysqlite:///:memory:"

@pytest.fixture
def app(tmp_path):
    TestConfig.UPLOAD_FOLDER = str(tmp_path / "uploads")
    app=create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):return app.test_client()
