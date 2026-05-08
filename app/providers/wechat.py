"""微信开放平台 PC 扫码登录（snsapi_login）适配器。

登录流程：
1. 前端跳转到 ``https://open.weixin.qq.com/connect/qrconnect?...`` 让用户扫码；
2. 微信将浏览器重定向回我们配置的 ``WECHAT_REDIRECT_URI?code=...&state=...``；
3. 后端用 code 换取 ``access_token`` 与 ``openid`` / ``unionid``；
4. 再用 ``access_token + openid`` 拉取用户公开资料（昵称、头像等）。
"""
from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlencode

import requests

from .. import config

AUTHORIZE_URL = "https://open.weixin.qq.com/connect/qrconnect"
ACCESS_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"


class WechatAuthError(RuntimeError):
    pass


def build_authorize_url(state: str) -> str:
    if not config.wechat_configured():
        raise WechatAuthError("微信登录未配置 (WECHAT_APP_ID / WECHAT_APP_SECRET / WECHAT_REDIRECT_URI)")
    params = {
        "appid": config.WECHAT_APP_ID,
        "redirect_uri": config.WECHAT_REDIRECT_URI,
        "response_type": "code",
        "scope": config.WECHAT_SCOPE,
        "state": state,
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}#wechat_redirect"


def _get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        resp = requests.get(url, params=params, timeout=8)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise WechatAuthError(f"请求微信接口失败: {exc}") from exc
    try:
        data = resp.json()
    except ValueError as exc:
        raise WechatAuthError("微信接口返回非 JSON") from exc
    if "errcode" in data and data.get("errcode"):
        raise WechatAuthError(f"微信接口错误: {data.get('errcode')} {data.get('errmsg')}")
    return data


def exchange_code_for_user(code: str) -> Dict[str, Any]:
    """code -> access_token -> userinfo. Returns a dict with openid/unionid/nickname/headimgurl."""
    if not config.wechat_configured():
        raise WechatAuthError("微信登录未配置")
    if not code:
        raise WechatAuthError("缺少 code 参数")

    token_data = _get_json(ACCESS_TOKEN_URL, {
        "appid": config.WECHAT_APP_ID,
        "secret": config.WECHAT_APP_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    })
    access_token = token_data.get("access_token")
    openid = token_data.get("openid")
    unionid = token_data.get("unionid")
    if not access_token or not openid:
        raise WechatAuthError("微信 access_token 返回不完整")

    user_data = _get_json(USERINFO_URL, {
        "access_token": access_token,
        "openid": openid,
        "lang": "zh_CN",
    })
    return {
        "openid": openid,
        "unionid": unionid or user_data.get("unionid"),
        "nickname": user_data.get("nickname"),
        "headimgurl": user_data.get("headimgurl"),
    }
