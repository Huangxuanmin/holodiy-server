"""阿里云 OSS SDK 的轻量封装。

职责：
- 把远程 URL（例如 Hitem3D 的签名下载链接）以流式方式直接转存到 OSS，
  不在磁盘或内存里缓存整个文件；
- 为私有读 bucket 生成带有效期的签名访问地址；
- 上传内存字节（用于原图归档等短小对象）；
- 删除指定对象（任务被删除时清理）。

``oss2`` 依赖是懒加载的 —— 即使服务运行环境没有配置 OSS，也不会影响其余
路由启动。
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


def build_source_key(user_id: str, task_id: str, index: int, ext: str = ".jpg") -> str:
    """Object key for an original uploaded source image.

    Layout: ``<source_prefix>/<user_id>/<task_id>/<index><ext>``.
    """
    safe_ext = ext if ext.startswith(".") else f".{ext}"
    return posixpath.join(
        config.OSS_SOURCE_KEY_PREFIX,
        user_id,
        task_id,
        f"{index}{safe_ext}",
    )


def upload_bytes(
    data: bytes,
    object_key: str,
    *,
    content_type: str = "application/octet-stream",
) -> int:
    """Upload in-memory bytes to OSS. Returns uploaded size."""
    bucket = _ensure_bucket()
    headers = {"Content-Type": content_type}
    logger.info("[oss] upload bytes: key=%s size=%d ctype=%s", object_key, len(data), content_type)
    result = bucket.put_object(object_key, data, headers=headers)
    if result.status // 100 != 2:
        raise OSSError(f"OSS put_object failed: http={result.status}")
    return len(data)


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
            content_type = resp.headers.get("Content-Type") or "application/octet-stream"

            # NOTE: 故意不转发上游的 Content-Length。
            # 上游若是 gzip/chunked 传输，requests 会自动解压，
            # iter_content 产出的字节数与响应头里的 Content-Length 不一致，
            # OSS 会以 400 BadRequest 拒绝。交给 oss2 以流式方式自行处理长度。
            headers = {"Content-Type": content_type}

            def _chunks():
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        yield chunk

            logger.info(
                "[oss] streaming upload: key=%s ctype=%s",
                object_key,
                content_type,
            )
            result = bucket.put_object(object_key, _chunks(), headers=headers)
            if result.status // 100 != 2:
                raise OSSError(f"OSS put_object failed: http={result.status}")
    except requests.RequestException as exc:
        raise OSSError(f"下载源文件失败: {exc}") from exc

    # Fetch authoritative size after upload (upstream Content-Length may be
    # missing or inaccurate, e.g. chunked transfer encoding or gzip).
    try:
        meta = bucket.head_object(object_key)
        return int(meta.content_length or 0)
    except Exception:  # noqa: BLE001
        return 0


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
    # Force https so the URL is usable from HTTPS front-ends (avoids mixed
    # content blocking). Aliyun OSS supports HTTPS on every bucket endpoint.
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
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
