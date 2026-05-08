"""Lightweight wrapper around the Aliyun OSS SDK.

Responsibilities:
- Stream a remote URL (e.g. Hitem3D signed download) straight into OSS
  without buffering the full file on disk or in memory.
- Generate time-limited signed URLs for private-read buckets.
- Delete objects (used when a task is removed).

``oss2`` is imported lazily so the rest of the server still boots when OSS
credentials are not configured.
"""
from __future__ import annotations

import logging
import posixpath
from typing import Optional

import requests

from . import config

logger = logging.getLogger(__name__)


class OSSError(Exception):
    """Raised for any OSS-side failure we want the app to surface."""


# Module-level singleton bucket, created on first use.
_bucket = None


def _ensure_bucket():
    global _bucket
    if _bucket is not None:
        return _bucket
    if not config.oss_configured():
        raise OSSError("OSS 尚未配置，请先在 .env 填写 OSS_* 变量")

    try:
        import oss2  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise OSSError("oss2 依赖未安装，请 pip install oss2") from exc

    auth = oss2.Auth(config.OSS_ACCESS_KEY_ID, config.OSS_ACCESS_KEY_SECRET)
    _bucket = oss2.Bucket(auth, config.OSS_ENDPOINT, config.OSS_BUCKET)
    return _bucket


def build_key(user_id: str, task_id: str, ext: str = ".obj") -> str:
    """Deterministic object key layout: ``<prefix>/<user_id>/<task_id><ext>``."""
    safe_ext = ext if ext.startswith(".") else f".{ext}"
    return posixpath.join(config.OSS_KEY_PREFIX, user_id, f"{task_id}{safe_ext}")


def upload_from_url(
    source_url: str,
    object_key: str,
    *,
    chunk_size: int = 1024 * 1024,
    timeout: int = 600,
) -> int:
    """Stream ``source_url`` → OSS object. Returns final file size in bytes.

    Uses OSS multipart via ``bucket.put_object`` with a generator: oss2 will
    read the generator lazily, so RAM stays ~chunk_size regardless of total
    file size.
    """
    bucket = _ensure_bucket()

    try:
        with requests.get(source_url, stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            content_length = resp.headers.get("Content-Length")
            content_type = resp.headers.get("Content-Type") or "application/octet-stream"

            headers = {"Content-Type": content_type}
            if content_length:
                headers["Content-Length"] = content_length

            def _chunks():
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        yield chunk

            logger.info(
                "[oss] streaming upload: key=%s size=%s ctype=%s",
                object_key,
                content_length or "unknown",
                content_type,
            )
            result = bucket.put_object(object_key, _chunks(), headers=headers)
            if result.status // 100 != 2:
                raise OSSError(f"OSS put_object failed: http={result.status}")
    except requests.RequestException as exc:
        raise OSSError(f"下载源文件失败: {exc}") from exc

    # Fetch authoritative size after upload (Content-Length from upstream may
    # be missing, e.g. chunked transfer encoding).
    try:
        meta = bucket.head_object(object_key)
        return int(meta.content_length or 0)
    except Exception:  # noqa: BLE001
        return int(content_length or 0)


def get_signed_url(object_key: str, expires: Optional[int] = None) -> str:
    """Return a time-limited signed GET URL for a private-read bucket."""
    bucket = _ensure_bucket()
    ttl = expires if expires is not None else config.OSS_SIGN_URL_TTL
    url = bucket.sign_url("GET", object_key, ttl, slash_safe=True)
    # If user configured a custom CDN/domain, swap the host while keeping the
    # signature query string (requires the CDN to be a CNAME of the bucket).
    if config.OSS_PUBLIC_BASE:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        public = urlparse(config.OSS_PUBLIC_BASE)
        url = urlunparse((
            public.scheme or parsed.scheme,
            public.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        ))
    return url


def delete_object(object_key: str) -> None:
    try:
        bucket = _ensure_bucket()
    except OSSError:
        return
    try:
        bucket.delete_object(object_key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[oss] delete_object failed: key=%s err=%s", object_key, exc)
