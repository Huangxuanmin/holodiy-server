"""阿里云短信服务 (Dysmsapi) adapter.

Lazily creates the client so missing credentials only fail when we actually
try to send.
"""
from __future__ import annotations

import json
import threading
from typing import Optional

from .. import config

_client_lock = threading.Lock()
_client = None  # type: ignore[var-annotated]


class SmsSendError(RuntimeError):
    pass


def _build_client():
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is not None:
            return _client
        if not config.sms_configured():
            raise SmsSendError("阿里云短信未配置 (ALIYUN_SMS_*)")

        # Import lazily — avoids forcing dependency when running tests without SDK.
        from alibabacloud_dysmsapi20170525.client import Client  # type: ignore
        from alibabacloud_tea_openapi import models as open_api_models  # type: ignore

        cfg = open_api_models.Config(
            access_key_id=config.ALIYUN_SMS_AK_ID,
            access_key_secret=config.ALIYUN_SMS_AK_SECRET,
            endpoint=config.ALIYUN_SMS_ENDPOINT,
            # 短信是同步请求，5s 连接 + 5s 读取，避免前端端超时前还在挂起
            connect_timeout=5000,
            read_timeout=5000,
        )
        _client = Client(cfg)
        return _client


def send_sms_code(phone: str, code: str, template_code: Optional[str] = None) -> None:
    """Send a verification code SMS. Raises SmsSendError on failure."""
    from alibabacloud_dysmsapi20170525 import models as sms_models  # type: ignore

    client = _build_client()
    template_param = json.dumps({config.ALIYUN_SMS_TEMPLATE_PARAM: code}, ensure_ascii=False)

    req = sms_models.SendSmsRequest(
        phone_numbers=phone,
        sign_name=config.ALIYUN_SMS_SIGN,
        template_code=template_code or config.ALIYUN_SMS_TEMPLATE,
        template_param=template_param,
    )
    try:
        resp = client.send_sms(req)
    except Exception as exc:  # network / SDK error
        raise SmsSendError(f"短信发送失败: {exc}") from exc

    body = getattr(resp, "body", None)
    if body is None:
        raise SmsSendError("短信发送失败: 无响应")
    status_code = getattr(body, "code", None)
    if status_code != "OK":
        message = getattr(body, "message", "未知错误")
        raise SmsSendError(f"短信发送失败: {status_code} {message}")
