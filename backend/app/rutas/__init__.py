from .administracion import admin_bp
from .autenticacion import auth_bp
from .categorias import category_bp
from .expositores import exhibitor_bp
from .ferias import fair_bp
from .productos import product_bp
from .portal_publico import public_bp
from .reportes import report_bp
from .archivos import upload_bp
from .sectores_productivos import productive_sector_bp
from .unidades_productivas import productive_unit_bp
from .solicitudes_registro import registration_bp


def registrar_rutas(app):
    for blueprint in (
        auth_bp,
        upload_bp,
        public_bp,
        admin_bp,
        fair_bp,
        category_bp,
        exhibitor_bp,
        product_bp,
        report_bp,
        registration_bp,
        productive_sector_bp,
        productive_unit_bp,
    ):
        app.register_blueprint(blueprint, url_prefix="/api")
