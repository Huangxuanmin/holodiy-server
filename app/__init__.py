"""Flask application factory for the Hogel API."""
import os

from flask import Flask
from flask_cors import CORS

from . import config
from .routes import api_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
    app.config["OUTPUT_FOLDER"] = config.OUTPUT_FOLDER
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.config["APP_PORT"] = config.APP_PORT

    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)

    app.register_blueprint(api_bp)

    return app
