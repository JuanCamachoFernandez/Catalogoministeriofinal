import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from .config import Config
from .extensions import db,migrate,jwt

def create_app(config=Config):
    load_dotenv(); app=Flask(__name__); app.config.from_object(config)
    os.makedirs(app.config["UPLOAD_FOLDER"],exist_ok=True)
    db.init_app(app); migrate.init_app(app,db); jwt.init_app(app); CORS(app,origins=app.config["CORS_ORIGINS"])
    from .api import api; app.register_blueprint(api,url_prefix="/api")
    @app.get("/api/health")
    def health(): return {"status":"ok"}
    @app.get("/uploads/<path:name>")
    def uploads(name): return send_from_directory(app.config["UPLOAD_FOLDER"],name)
    from .commands import register_commands; register_commands(app)
    return app
