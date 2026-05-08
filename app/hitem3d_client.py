"""Thin client wrapper around the Hitem3D open platform API."""
from __future__ import annotations

import base64
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from . import config

logger = logging.getLogger(__name__)


class Hitem3DError(Exception):
    """Raised when the upstream Hitem3D API returns a non-success payload."""

    def __init__(self, message: str, code: Optional[int] = None, status: int = 502):
        super().__init__(message)
        self.code = code
        self.status = status


# Tokens from the docs appear to be long-lived but no explicit TTL is given.
# Refresh every hour to be safe.
_TOKEN_TTL_SECONDS = 55 * 60

_token_lock = threading.Lock()
_token_cache: Dict[str, Any] = {"token": None, "expires_at": 0.0}


def _basic_auth_header() -> str:
    if not config.hitem3d_configured():
        raise Hitem3DError("Hitem3D credentials are not configured", status=500)
    raw = f"{config.HITEM3D_CLIENT_ID}:{config.HITEM3D_CLIENT_SECRET}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _parse_payload(resp: requests.Response) -> Dict[str, Any]:
    try:
        payload = resp.json()
    except ValueError as exc:
        logger.error(
            "Hitem3D non-JSON response: status=%s body=%s",
            resp.status_code,
            resp.text[:500],
        )
        raise Hitem3DError(
            f"Invalid JSON from Hitem3D (status={resp.status_code}): {resp.text[:200]}",
            status=502,
        ) from exc

    code = payload.get("code")
    if code not in (200, 0, "200", "0"):
        message = payload.get("msg") or payload.get("message") or "Hitem3D API error"
        logger.error(
            "Hitem3D business error: http=%s code=%s msg=%s payload=%s",
            resp.status_code,
            code,
            message,
            payload,
        )
        raise Hitem3DError(message, code=code if isinstance(code, int) else None, status=502)
    return payload


def get_access_token(force_refresh: bool = False) -> str:
    """Get a (cached) access token from the Hitem3D platform."""
    now = time.time()
    with _token_lock:
        if (
            not force_refresh
            and _token_cache.get("token")
            and now < _token_cache.get("expires_at", 0)
        ):
            return _token_cache["token"]

        url = f"{config.HITEM3D_BASE_URL}/open-api/v1/auth/token"
        headers = {
            "Authorization": _basic_auth_header(),
            "Content-Type": "application/json",
            "Accept": "*/*",
        }
        try:
            resp = requests.post(url, headers=headers, json={}, timeout=30)
        except requests.RequestException as exc:
            raise Hitem3DError(f"token request failed: {exc}", status=502) from exc

        payload = _parse_payload(resp)
        token = (payload.get("data") or {}).get("accessToken")
        if not token:
            raise Hitem3DError("token missing in response", status=502)

        _token_cache["token"] = token
        _token_cache["expires_at"] = now + _TOKEN_TTL_SECONDS
        return token


def _auth_headers(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {get_access_token()}",
        "Accept": "*/*",
    }
    if extra:
        headers.update(extra)
    return headers


def submit_task(
    form_fields: Dict[str, str],
    images: List[Tuple[str, bytes, str]],
    multi_images: List[Tuple[str, bytes, str]],
) -> Dict[str, Any]:
    """Submit an image-to-3D task. `images` / `multi_images` are (filename, bytes, mime) tuples."""
    url = f"{config.HITEM3D_BASE_URL}/open-api/v1/submit-task"

    files: List[Tuple[str, Tuple[str, bytes, str]]] = []
    for filename, data, mime in images:
        files.append(("images", (filename, data, mime)))
    for filename, data, mime in multi_images:
        files.append(("multi_images", (filename, data, mime)))

    def _do_request(token_refreshed: bool = False) -> Dict[str, Any]:
        try:
            resp = requests.post(
                url,
                headers=_auth_headers(),
                data=form_fields,
                files=files,
                timeout=120,
            )
        except requests.RequestException as exc:
            raise Hitem3DError(f"submit-task failed: {exc}", status=502) from exc

        logger.info(
            "Hitem3D submit-task http=%s form_keys=%s file_fields=%s",
            resp.status_code,
            list(form_fields.keys()),
            [f[0] for f in files],
        )

        # Token possibly expired — try one forced refresh then retry.
        if resp.status_code == 401 and not token_refreshed:
            get_access_token(force_refresh=True)
            return _do_request(token_refreshed=True)

        return _parse_payload(resp)

    return _do_request()


def query_task(task_id: str) -> Dict[str, Any]:
    url = f"{config.HITEM3D_BASE_URL}/open-api/v1/query-task"
    try:
        resp = requests.get(
            url,
            headers=_auth_headers(),
            params={"task_id": task_id},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise Hitem3DError(f"query-task failed: {exc}", status=502) from exc

    if resp.status_code == 401:
        get_access_token(force_refresh=True)
        resp = requests.get(
            url,
            headers=_auth_headers(),
            params={"task_id": task_id},
            timeout=30,
        )

    return _parse_payload(resp)
