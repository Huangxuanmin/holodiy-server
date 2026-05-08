"""鉴权相关路由。

涵盖：密码登录、手机号 / 邮箱验证码登录与注册、微信 PC 扫码登录（snsapi_login）、
当前用户信息查询、登出等。
同时提供 ``token_required`` 装饰器，用于保护其他需要登录的路由。
"""
from __future__ import annotations

import logging
import re
import secrets
import threading
import time
from functools import wraps
from typing import Optional
from urllib.parse import urlencode

from flask import Blueprint, g, redirect, request

from . import auth_store, config, rate_limit
from .providers.email_aliyun import EmailSendError, send_email_code as _send_email_code
from .providers.sms_aliyun import SmsSendError, send_sms_code as _send_sms_code
from .providers.wechat import WechatAuthError, build_authorize_url, exchange_code_for_user
from .responses import err as _err, ok as _ok

log = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^1[3-9]\d{9}$")  # 中国大陆手机号


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _json() -> dict:
    return request.get_json(silent=True) or {}


def _auth_response(user: dict):
    token = auth_store.issue_token(user["id"])
    return _ok({"token": token, "user": auth_store.public_user(user)})


def _valid_email(value: Optional[str]) -> bool:
    return bool(value and EMAIL_RE.match(value))


def _valid_phone(value: Optional[str]) -> bool:
    return bool(value and PHONE_RE.match(value))


def token_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = header[7:].strip() if header.lower().startswith("bearer ") else ""
        user = auth_store.resolve_token(token)
        if not user:
            return _err("未登录或登录已过期", status=401, http_code=401)
        g.current_user = user
        g.current_token = token
        return func(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------

@auth_bp.route("/register", methods=["POST"])
def register():
    """邮箱密码或手机号密码注册。"""
    payload = _json()
    email = (payload.get("email") or "").strip().lower() or None
    phone = (payload.get("phone") or "").strip() or None
    password = payload.get("password") or ""
    name = (payload.get("name") or "").strip() or None

    if not email and not phone:
        return _err("请提供邮箱或手机号")
    if email and not _valid_email(email):
        return _err("邮箱格式不正确")
    if phone and not _valid_phone(phone):
        return _err("手机号格式不正确")
    if len(password) < 6:
        return _err("密码至少 6 位")

    if email and auth_store.find_user(email=email):
        return _err("该邮箱已被注册")
    if phone and auth_store.find_user(phone=phone):
        return _err("该手机号已被注册")

    user = auth_store.create_user(email=email, phone=phone, password=password, name=name)
    return _auth_response(user)


@auth_bp.route("/login/password", methods=["POST"])
def login_password():
    """邮箱/手机号 + 密码 登录。"""
    payload = _json()
    account = (payload.get("account") or payload.get("email") or payload.get("phone") or "").strip()
    password = payload.get("password") or ""

    if not account or not password:
        return _err("请输入账号和密码")

    lookup = {}
    if EMAIL_RE.match(account):
        lookup["email"] = account.lower()
    elif PHONE_RE.match(account):
        lookup["phone"] = account
    else:
        return _err("账号格式不正确，请输入邮箱或手机号")

    user = auth_store.find_user(**lookup)
    if not user or not auth_store.verify_password(user, password):
        return _err("账号或密码错误")

    return _auth_response(user)


@auth_bp.route("/send-sms-code", methods=["POST"])
def send_sms_code():
    """发送手机验证码。"""
    phone = (_json().get("phone") or "").strip()
    if not _valid_phone(phone):
        return _err("手机号格式不正确")

    allowed, reason = rate_limit.check(f"sms:{phone}", per_minute=1, per_day=10)
    if not allowed:
        return _err(reason, http_code=429)

    code = auth_store.generate_code(f"sms:{phone}")
    data = None

    if config.sms_configured():
        try:
            _send_sms_code(phone, code)
        except SmsSendError as exc:
            log.exception("sms send failed for %s", phone)
            return _err(str(exc), http_code=502)
    elif config.AUTH_PROVIDER_DEV_FALLBACK:
        log.warning("[DEV] SMS provider not configured, code for %s: %s", phone, code)
        data = {"devCode": code}
    else:
        return _err("短信服务未配置，请联系管理员", http_code=503)

    return _ok(data, msg="验证码已发送")


@auth_bp.route("/login/sms", methods=["POST"])
def login_sms():
    """短信验证码登录；不存在则自动创建账号。"""
    payload = _json()
    phone = (payload.get("phone") or "").strip()
    code = (payload.get("code") or "").strip()

    if not _valid_phone(phone):
        return _err("手机号格式不正确")
    if not code:
        return _err("请输入验证码")
    if not auth_store.verify_code(f"sms:{phone}", code):
        return _err("验证码不正确或已过期")

    user = auth_store.find_user(phone=phone)
    if not user:
        user = auth_store.create_user(phone=phone)
    return _auth_response(user)


@auth_bp.route("/send-email-code", methods=["POST"])
def send_email_code():
    """发送邮箱验证码。"""
    email = (_json().get("email") or "").strip().lower()
    if not _valid_email(email):
        return _err("邮箱格式不正确")

    allowed, reason = rate_limit.check(f"email:{email}", per_minute=1, per_day=10)
    if not allowed:
        return _err(reason, http_code=429)

    code = auth_store.generate_code(f"email:{email}")
    data = None

    if config.email_configured():
        try:
            _send_email_code(email, code)
        except EmailSendError as exc:
            log.exception("email send failed for %s", email)
            return _err(str(exc), http_code=502)
    elif config.AUTH_PROVIDER_DEV_FALLBACK:
        log.warning("[DEV] Email provider not configured, code for %s: %s", email, code)
        data = {"devCode": code}
    else:
        return _err("邮件服务未配置，请联系管理员", http_code=503)

    return _ok(data, msg="验证码已发送")


@auth_bp.route("/login/email-code", methods=["POST"])
def login_email_code():
    """邮箱验证码登录；不存在则自动创建账号。"""
    payload = _json()
    email = (payload.get("email") or "").strip().lower()
    code = (payload.get("code") or "").strip()

    if not _valid_email(email):
        return _err("邮箱格式不正确")
    if not code:
        return _err("请输入邮箱验证码")
    if not auth_store.verify_code(f"email:{email}", code):
        return _err("验证码不正确或已过期")

    user = auth_store.find_user(email=email)
    if not user:
        user = auth_store.create_user(email=email)
    return _auth_response(user)


@auth_bp.route("/register/email-code", methods=["POST"])
def register_email_code():
    """邮箱验证码注册（可设置初始密码）。"""
    payload = _json()
    email = (payload.get("email") or "").strip().lower()
    code = (payload.get("code") or "").strip()
    password = payload.get("password") or ""
    name = (payload.get("name") or "").strip() or None

    if not _valid_email(email):
        return _err("邮箱格式不正确")
    if not code:
        return _err("请输入邮箱验证码")
    if password and len(password) < 6:
        return _err("密码至少 6 位")
    if not auth_store.verify_code(f"email:{email}", code):
        return _err("验证码不正确或已过期")

    user = auth_store.find_user(email=email)
    if user:
        return _err("该邮箱已被注册")

    user = auth_store.create_user(email=email, password=password or None, name=name)
    return _auth_response(user)


@auth_bp.route("/oauth/google", methods=["POST"])
def oauth_google():
    """Google 登录（demo: 接受前端传入的 profile，或 credential 的 sub/email）。

    真实环境应调用 Google tokeninfo 验证 id_token。"""
    payload = _json()
    provider_uid = (payload.get("sub") or payload.get("id") or "").strip()
    email = (payload.get("email") or "").strip().lower() or None
    name = (payload.get("name") or "").strip() or None
    avatar = (payload.get("picture") or payload.get("avatar") or "").strip() or None

    if not provider_uid and not email:
        return _err("Google 登录参数缺失")

    user = auth_store.find_user(provider="google", provider_uid=provider_uid) if provider_uid else None
    if not user and email:
        user = auth_store.find_user(email=email)
        if user and provider_uid:
            auth_store.link_oauth(user["id"], "google", provider_uid)
            user = auth_store.find_user(email=email)

    if not user:
        user = auth_store.create_user(
            email=email,
            name=name,
            avatar=avatar,
            provider="google",
            provider_uid=provider_uid or f"google:{email}",
        )

    return _auth_response(user)


@auth_bp.route("/oauth/wechat", methods=["POST"])
def oauth_wechat():
    """微信登录（demo: 接受 openid / unionid / 用户信息）。

    真实环境应使用 code 换取 access_token，再拉取用户信息。"""
    payload = _json()
    provider_uid = (payload.get("unionid") or payload.get("openid") or "").strip()
    name = (payload.get("nickname") or payload.get("name") or "").strip() or None
    avatar = (payload.get("headimgurl") or payload.get("avatar") or "").strip() or None

    if not provider_uid:
        return _err("微信登录参数缺失")

    user = auth_store.find_user(provider="wechat", provider_uid=provider_uid)
    if not user:
        user = auth_store.create_user(
            name=name,
            avatar=avatar,
            provider="wechat",
            provider_uid=provider_uid,
        )

    return _auth_response(user)


# --- WeChat PC QR login (snsapi_login) -------------------------------------

_WECHAT_STATE_TTL = 10 * 60  # 10 minutes
_wechat_states: dict[str, float] = {}
_wechat_states_lock = threading.Lock()


def _wechat_issue_state() -> str:
    state = secrets.token_urlsafe(16)
    now = time.time()
    with _wechat_states_lock:
        # opportunistic GC
        expired = [k for k, v in _wechat_states.items() if v < now]
        for k in expired:
            _wechat_states.pop(k, None)
        _wechat_states[state] = now + _WECHAT_STATE_TTL
    return state


def _wechat_consume_state(state: str) -> bool:
    if not state:
        return False
    with _wechat_states_lock:
        expires = _wechat_states.pop(state, None)
    return bool(expires and expires >= time.time())


@auth_bp.route("/wechat/authorize", methods=["GET"])
def wechat_authorize():
    """返回微信二维码登录页 URL，由前端跳转（或 ?redirect=1 时服务端直接 302）。"""
    if not config.wechat_configured():
        return _err("微信登录未配置", http_code=503)
    try:
        state = _wechat_issue_state()
        url = build_authorize_url(state)
    except WechatAuthError as exc:
        return _err(str(exc), http_code=503)

    if request.args.get("redirect") in {"1", "true"}:
        return redirect(url, code=302)
    return _ok({"url": url, "state": state})


@auth_bp.route("/wechat/callback", methods=["GET"])
def wechat_callback():
    """微信授权回调。换取用户信息 → 登录/注册 → 302 到前端并带上 token。"""
    code = (request.args.get("code") or "").strip()
    state = (request.args.get("state") or "").strip()
    frontend = config.WECHAT_FRONTEND_REDIRECT or "/"

    def _redirect_fail(msg: str):
        sep = "&" if "?" in frontend else "?"
        return redirect(f"{frontend}{sep}{urlencode({'error': msg})}", code=302)

    if not code:
        return _redirect_fail(request.args.get("error") or "wechat_no_code")
    if not _wechat_consume_state(state):
        return _redirect_fail("invalid_state")

    try:
        profile = exchange_code_for_user(code)
    except WechatAuthError as exc:
        log.warning("wechat exchange failed: %s", exc)
        return _redirect_fail("wechat_exchange_failed")

    provider_uid = profile.get("unionid") or profile.get("openid")
    if not provider_uid:
        return _redirect_fail("wechat_no_openid")

    user = auth_store.find_user(provider="wechat", provider_uid=provider_uid)
    if not user:
        user = auth_store.create_user(
            name=profile.get("nickname"),
            avatar=profile.get("headimgurl"),
            provider="wechat",
            provider_uid=provider_uid,
        )
    token = auth_store.issue_token(user["id"])
    sep = "&" if "?" in frontend else "?"
    return redirect(f"{frontend}{sep}{urlencode({'token': token})}", code=302)


@auth_bp.route("/me", methods=["GET"])
@token_required
def me():
    return _ok({"user": auth_store.public_user(g.current_user)})


@auth_bp.route("/logout", methods=["POST"])
@token_required
def logout():
    auth_store.revoke_token(g.current_token)
    return _ok(msg="已退出登录")
