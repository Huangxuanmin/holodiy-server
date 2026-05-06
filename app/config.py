"""Configuration constants for the Hogel API."""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "bmp"}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
APP_PORT = 8000
