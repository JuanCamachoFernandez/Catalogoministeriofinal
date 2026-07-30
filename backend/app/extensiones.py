from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from sqlalchemy import MetaData

CONVENCION_NOMBRES = {
    "ix": "indice_%(table_name)s_%(column_0_name)s",
    "uq": "unico_%(table_name)s_%(column_0_name)s",
    "ck": "verificacion_%(table_name)s_%(constraint_name)s",
    "fk": "foranea_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "primaria_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=CONVENCION_NOMBRES))
migrate = Migrate()
jwt = JWTManager()

