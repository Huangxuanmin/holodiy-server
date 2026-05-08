"""项目全局配置。

在导入时读取 ``holodiy-server/.env``，把所有对外可配置的环境变量集中成模块
级常量（上传目录、Hitem3D / OSS / 阿里云短信邮件 / 微信登录等）。
其他模块统一从这里 ``from . import config`` 取值，避免到处 ``os.environ``。
"""
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

# --- WeChat open platform (PC QR login, snsapi_login) ----------------------
# 在 https://open.weixin.qq.com 创建「网站应用」后获得 AppID / AppSecret，
# 并在"授权回调域"中登记回调域名（只填一级域名，不带协议/路径）。
WECHAT_APP_ID = os.environ.get("WECHAT_APP_ID", "").strip()
WECHAT_APP_SECRET = os.environ.get("WECHAT_APP_SECRET", "").strip()
# 完整的回调 URL，必须落在已登记的"授权回调域"下。例：
# https://yourdomain.com/api/auth/wechat/callback
WECHAT_REDIRECT_URI = os.environ.get("WECHAT_REDIRECT_URI", "").strip()
# 登录成功后把 token 带回到前端的哪个页面（前端路由）。
# 例：https://yourdomain.com/auth/wechat/callback
WECHAT_FRONTEND_REDIRECT = os.environ.get(
    "WECHAT_FRONTEND_REDIRECT", "http://localhost:5173/auth/wechat/callback"
).strip()
WECHAT_SCOPE = os.environ.get("WECHAT_SCOPE", "snsapi_login").strip() or "snsapi_login"

# --- Hitem3D API ----------------------------------------------------------
HITEM3D_CLIENT_ID = os.environ.get("HITEM3D_CLIENT_ID", "").strip()
HITEM3D_CLIENT_SECRET = os.environ.get("HITEM3D_CLIENT_SECRET", "").strip()
HITEM3D_BASE_URL = os.environ.get(
    "HITEM3D_BASE_URL", "https://api.hitem3d.ai"
).strip().rstrip("/")


# --- Aliyun OSS (generated 3D model storage) -------------------------------
OSS_ACCESS_KEY_ID = os.environ.get("OSS_ACCESS_KEY_ID", "").strip()
OSS_ACCESS_KEY_SECRET = os.environ.get("OSS_ACCESS_KEY_SECRET", "").strip()
OSS_BUCKET = os.environ.get("OSS_BUCKET", "").strip()
OSS_ENDPOINT = os.environ.get("OSS_ENDPOINT", "").strip()
OSS_PUBLIC_BASE = os.environ.get("OSS_PUBLIC_BASE", "").strip().rstrip("/")
OSS_KEY_PREFIX = os.environ.get("OSS_KEY_PREFIX", "hitem3d").strip().strip("/") or "hitem3d"
OSS_SOURCE_KEY_PREFIX = os.environ.get("OSS_SOURCE_KEY_PREFIX", "sources").strip().strip("/") or "sources"
try:
    OSS_SIGN_URL_TTL = int(os.environ.get("OSS_SIGN_URL_TTL", "3600").strip() or 3600)
except ValueError:
    OSS_SIGN_URL_TTL = 3600


def oss_configured() -> bool:
    return all([OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_BUCKET, OSS_ENDPOINT])


def hitem3d_configured() -> bool:
    return bool(HITEM3D_CLIENT_ID and HITEM3D_CLIENT_SECRET)


def sms_configured() -> bool:
    return all([ALIYUN_SMS_AK_ID, ALIYUN_SMS_AK_SECRET, ALIYUN_SMS_SIGN, ALIYUN_SMS_TEMPLATE])


def email_configured() -> bool:
    return all([ALIYUN_DM_AK_ID, ALIYUN_DM_AK_SECRET, ALIYUN_DM_ACCOUNT])


def wechat_configured() -> bool:
    return all([WECHAT_APP_ID, WECHAT_APP_SECRET, WECHAT_REDIRECT_URI])
