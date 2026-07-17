from .admin_controller import admin_bp
from .auth_controller import auth_bp
from .category_controller import category_bp
from .exhibitor_controller import exhibitor_bp
from .fair_controller import fair_bp
from .product_controller import product_bp
from .public_controller import public_bp
from .upload_controller import upload_bp


def register_controllers(app):
    for blueprint in (
        auth_bp,
        upload_bp,
        public_bp,
        admin_bp,
        fair_bp,
        category_bp,
        exhibitor_bp,
        product_bp,
    ):
        app.register_blueprint(blueprint, url_prefix="/api")
