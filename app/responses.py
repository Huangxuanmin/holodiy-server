"""Unified API response helpers.

All JSON responses should follow the shape::

    {"status": <int>, "msg": <str>, "data": <any>}

Where ``status == 0`` means success and any non-zero value means a business
error. Frontend interceptors rely on this shape to surface the ``msg`` via
toast when ``status != 0``.
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
