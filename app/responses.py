"""统一的 API 响应封装。

所有 JSON 响应都遵循如下结构::

    {"status": <int>, "msg": <str>, "data": <any>}

其中 ``status == 0`` 表示成功，其余值表示业务错误；前端请求拦截器会在
``status != 0`` 时自动通过 toast 弹出 ``msg``。
"""
from __future__ import annotations

from typing import Any

from flask import jsonify


def ok(data: Any = None, msg: str = "ok"):
    """Return a successful JSON response."""
    return jsonify({"status": 0, "msg": msg, "data": data})


def err(msg: str, status: int = 1, http_code: int = 400, data: Any = None):
    """Return a failed JSON response.

    ``status`` is the business code (non-zero); ``http_code`` is the HTTP code.
    """
    return jsonify({"status": status, "msg": msg, "data": data}), http_code
