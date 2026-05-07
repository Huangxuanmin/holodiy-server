"""阿里云邮件推送 (DirectMail) adapter."""
from __future__ import annotations

import threading
from typing import Optional

from .. import config

_client_lock = threading.Lock()
_client = None  # type: ignore[var-annotated]


class EmailSendError(RuntimeError):
    pass


def _build_client():
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is not None:
            return _client
        if not config.email_configured():
            raise EmailSendError("阿里云邮件推送未配置 (ALIYUN_DM_*)")

        from alibabacloud_dm20151123.client import Client  # type: ignore
        from alibabacloud_tea_openapi import models as open_api_models  # type: ignore

        cfg = open_api_models.Config(
            access_key_id=config.ALIYUN_DM_AK_ID,
            access_key_secret=config.ALIYUN_DM_AK_SECRET,
            endpoint=config.ALIYUN_DM_ENDPOINT,
            connect_timeout=5000,
            read_timeout=8000,
        )
        _client = Client(cfg)
        return _client


_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
  <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'PingFang SC','Hiragino Sans GB',sans-serif;background:#0a0c10;margin:0;padding:32px 0;">
    <div style="max-width:480px;margin:0 auto;background:#ffffff;border-radius:16px;padding:32px;">
      <h1 style="margin:0 0 16px;font-size:20px;color:#111827;">HoloDIY 验证码</h1>
      <p style="margin:0 0 16px;color:#374151;font-size:14px;line-height:1.6;">
        您好，您正在进行邮箱验证操作。请在 5 分钟内完成验证：
      </p>
      <div style="margin:24px 0;text-align:center;">
        <span style="display:inline-block;padding:16px 32px;font-size:28px;letter-spacing:8px;font-weight:700;color:#111827;background:#f3f4f6;border-radius:12px;">{code}</span>
      </div>
      <p style="margin:0;color:#6b7280;font-size:12px;line-height:1.6;">
        如果这不是您本人的操作，请忽略此邮件。本邮件由系统自动发送，请勿直接回复。
      </p>
    </div>
  </body>
</html>
""".strip()


def send_email_code(to_email: str, code: str, subject: Optional[str] = None) -> None:
    """Send a verification code via DirectMail SingleSendMail API."""
    from alibabacloud_dm20151123 import models as dm_models  # type: ignore

    client = _build_client()
    req = dm_models.SingleSendMailRequest(
        account_name=config.ALIYUN_DM_ACCOUNT,
        from_alias=config.ALIYUN_DM_FROM_ALIAS or "HoloDIY",
        address_type=1,          # 1=使用发信地址发送
        reply_to_address=False,
        to_address=to_email,
        subject=subject or "HoloDIY 邮箱验证码",
        html_body=_HTML_TEMPLATE.format(code=code),
    )
    try:
        client.single_send_mail(req)
    except Exception as exc:
        raise EmailSendError(f"邮件发送失败: {exc}") from exc
