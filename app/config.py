"""Configuration constants for the Hogel API."""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load .env once at import time (safe no-op in production if file missing).
load_dotenv(os.path.join(BASE_DIR, ".env"))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "bmp"}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
APP_PORT = 8000

# --- Auth provider config --------------------------------------------------

ALIYUN_SMS_AK_ID = os.environ.get("ALIYUN_SMS_AK_ID", "").strip()
ALIYUN_SMS_AK_SECRET = os.environ.get("ALIYUN_SMS_AK_SECRET", "").strip()
ALIYUN_SMS_SIGN = os.environ.get("ALIYUN_SMS_SIGN", "").strip()
ALIYUN_SMS_TEMPLATE = os.environ.get("ALIYUN_SMS_TEMPLATE", "").strip()
ALIYUN_SMS_TEMPLATE_PARAM = os.environ.get("ALIYUN_SMS_TEMPLATE_PARAM", "code").strip() or "code"
ALIYUN_SMS_ENDPOINT = os.environ.get("ALIYUN_SMS_ENDPOINT", "dysmsapi.aliyuncs.com").strip()

ALIYUN_DM_AK_ID = os.environ.get("ALIYUN_DM_AK_ID", "").strip()
ALIYUN_DM_AK_SECRET = os.environ.get("ALIYUN_DM_AK_SECRET", "").strip()
ALIYUN_DM_ACCOUNT = os.environ.get("ALIYUN_DM_ACCOUNT", "").strip()
ALIYUN_DM_FROM_ALIAS = os.environ.get("ALIYUN_DM_FROM_ALIAS", "HoloDIY").strip()
ALIYUN_DM_ENDPOINT = os.environ.get("ALIYUN_DM_ENDPOINT", "dm.aliyuncs.com").strip()

AUTH_PROVIDER_DEV_FALLBACK = os.environ.get(
    "AUTH_PROVIDER_DEV_FALLBACK", "false"
).strip().lower() in {"1", "true", "yes", "on"}


def sms_configured() -> bool:
    return all([ALIYUN_SMS_AK_ID, ALIYUN_SMS_AK_SECRET, ALIYUN_SMS_SIGN, ALIYUN_SMS_TEMPLATE])


def email_configured() -> bool:
    return all([ALIYUN_DM_AK_ID, ALIYUN_DM_AK_SECRET, ALIYUN_DM_ACCOUNT])
