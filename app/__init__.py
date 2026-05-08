"""Flask 应用工厂。

职责：
- 初始化 Flask app、日志、数据库、上传/输出目录；
- 注册所有蓝图（图像处理、鉴权、Hitem3D、统一资产库）；
- 从 .env 读取配置，供各模块懒加载使用。
"""
import logging
import os

from flask import Flask
from flask_cors import CORS

from . import auth_store, config, task_store
from .assets_routes import assets_bp
from .auth_routes import auth_bp
from .db import init_db
from .hitem3d_routes import hitem3d_bp
from .routes import api_bp


def create_app() -> Flask:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Initialize SQLite schema, then best-effort import legacy JSON data.
    init_db()
    auth_store._migrate_json_to_sqlite()
    task_store._migrate_json_to_sqlite()

    app = Flask(__name__)
    CORS(app)

    app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
    app.config["OUTPUT_FOLDER"] = config.OUTPUT_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.config["APP_PORT"] = config.APP_PORT

    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)

    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(hitem3d_bp)
    app.register_blueprint(assets_bp)

    return app
