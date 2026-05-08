"""Hitem3D 图生 3D 相关路由。

涵盖：
- ``POST /submit``：转发生成请求，同时压缩并把用户原图存档到 OSS；
- ``GET /query``：透传查询并在必要时触发 OSS 转存；
- 后台线程：把 Hitem3D 签名下载地址流式上传到我们自己的 OSS；
- ``DELETE /tasks/<id>``：删除任务并清理 OSS 对象；
- ``POST /tasks/<id>/sources``：历史任务补传原图入口；
- ``GET /thumb/<name>``：本地首图缩略图访问。
"""
from __future__ import annotations

import logging
import posixpath
import threading
import traceback
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from flask import Blueprint, g, request, send_file

from . import config, oss_client, task_store
from .auth_routes import token_required
from .hitem3d_client import Hitem3DError, query_task, submit_task
from .responses import err as _err, ok as _ok
from .utils import compress_image_bytes

logger = logging.getLogger(__name__)

hitem3d_bp = Blueprint("hitem3d", __name__, url_prefix="/api/image-to-3d")


_ALLOWED_MIME = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}

# Fields forwarded to the upstream Hitem3D submit-task endpoint as-is
# (when present in the incoming multipart form).
_PASSTHROUGH_FIELDS = {
    "type",
    "model",
    "request_type",
    "resolution",
    "face",
    "format",
    "pbr",
    "geometry_mode",
    "texture_mode",
    "remove_shadow",
    "geometry_repair",
    "uv_expand",
    "callback_url",
    "mesh_url",
}


def _collect_files(key: str) -> List[Tuple[str, bytes, str]]:
    items: List[Tuple[str, bytes, str]] = []
    for f in request.files.getlist(key):
        if not f or not f.filename:
            continue
        mime = (f.mimetype or "application/octet-stream").lower()
        if mime not in _ALLOWED_MIME:
            raise Hitem3DError(
                f"Unsupported image type: {mime}. Only png/jpeg/webp allowed.",
                status=400,
            )
        data = f.read()
        items.append((f.filename, data, mime))
    return items


# ---------------------------------------------------------------------------
# OSS upload (runs in a background thread)
# ---------------------------------------------------------------------------

# Track upload threads to avoid double-scheduling for the same task.
_upload_jobs: dict[str, threading.Thread] = {}
_upload_jobs_lock = threading.Lock()


def _guess_ext_from_url(url: str) -> str:
    path = urlparse(url).path
    ext = posixpath.splitext(path)[1]
    return ext.lower() if ext else ".obj"


def _background_upload(user_id: str, task_id: str, source_url: str) -> None:
    """Stream Hitem3D ``source_url`` into OSS and flip ``upload_state`` to done."""
    try:
        ext = _guess_ext_from_url(source_url)
        oss_key = oss_client.build_key(user_id, task_id, ext=ext)
        task_store.update_upload(task_id, upload_state="uploading", oss_key=oss_key)

        logger.info("[hitem3d.upload] start task=%s key=%s", task_id, oss_key)
        size = oss_client.upload_from_url(source_url, oss_key)
        task_store.update_upload(
            task_id,
            upload_state="done",
            oss_key=oss_key,
            file_size=size,
            upload_error="",  # clear any previous error
        )
        logger.info("[hitem3d.upload] done task=%s size=%s", task_id, size)
    except Exception as exc:  # noqa: BLE001
        logger.error("[hitem3d.upload] failed task=%s: %s", task_id, exc)
        task_store.update_upload(
            task_id,
            upload_state="failed",
            upload_error=str(exc)[:500],
        )
    finally:
        with _upload_jobs_lock:
            _upload_jobs.pop(task_id, None)


def _schedule_oss_upload(user_id: str, task_id: str, source_url: str) -> None:
    if not source_url or not config.oss_configured():
        if not config.oss_configured():
            logger.warning("[hitem3d.upload] OSS 未配置，跳过 task=%s", task_id)
        return

    record = task_store.get_task(task_id)
    if not record:
        return
    # Skip if already uploaded or currently uploading.
    if record.get("upload_state") in {"done", "uploading"}:
        return

    with _upload_jobs_lock:
        if task_id in _upload_jobs and _upload_jobs[task_id].is_alive():
            return
        thread = threading.Thread(
            target=_background_upload,
            args=(user_id, task_id, source_url),
            daemon=True,
            name=f"hitem3d-upload-{task_id[:8]}",
        )
        _upload_jobs[task_id] = thread
        thread.start()


# ---------------------------------------------------------------------------
# response shaping
# ---------------------------------------------------------------------------

def _sign_model_url(record: dict) -> Optional[str]:
    """Return a fresh signed OSS URL if the file is in our bucket."""
    if record.get("upload_state") == "done" and record.get("oss_key"):
        try:
            return oss_client.get_signed_url(record["oss_key"])
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[hitem3d] sign_url failed task=%s err=%s",
                record.get("task_id"),
                exc,
            )
    return None


def _sign_source_urls(record: dict) -> List[str]:
    """Return fresh signed URLs for every stored source image."""
    keys = record.get("source_keys") or []
    if not keys or not config.oss_configured():
        return []
    signed: List[str] = []
    for key in keys:
        try:
            signed.append(oss_client.get_signed_url(key))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[hitem3d] sign source url failed task=%s key=%s err=%s",
                record.get("task_id"), key, exc,
            )
    return signed


def _upload_sources(
    user_id: str,
    task_id: str,
    images: List[Tuple[str, bytes, str]],
) -> List[str]:
    """Compress & upload original images to OSS. Returns list of OSS keys.

    Errors are logged but do not abort the overall flow — original images are a
    best-effort archive, not a hard requirement.
    """
    if not images or not config.oss_configured():
        return []
    keys: List[str] = []
    for index, (_name, data, _mime) in enumerate(images):
        try:
            body, ctype, ext = compress_image_bytes(data)
            key = oss_client.build_source_key(user_id, task_id, index, ext=ext)
            oss_client.upload_bytes(body, key, content_type=ctype)
            keys.append(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[hitem3d.sources] upload failed task=%s index=%d err=%s",
                task_id, index, exc,
            )
    return keys


def _shape_record(record: dict) -> dict:
    """Attach signed download URL and drop raw Hitem3D URL from the wire."""
    shaped = dict(record)
    signed = _sign_model_url(record)
    if signed:
        shaped["model_url"] = signed
    # If OSS is configured but upload isn't done yet, don't leak the upstream
    # (possibly already-expired) Hitem3D URL to the client.
    elif config.oss_configured() and record.get("upload_state") != "done":
        shaped["model_url"] = None
    shaped["source_images"] = _sign_source_urls(record)
    return shaped


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------

@hitem3d_bp.route("/submit", methods=["POST"])
@token_required
def submit():
    try:
        images = _collect_files("images")
        multi_images = _collect_files("multi_images")

        if not images and not multi_images:
            return _err("No images provided (expect 'images' or 'multi_images').")

        form_fields = {
            key: value
            for key, value in request.form.items()
            if key in _PASSTHROUGH_FIELDS and value is not None and value != ""
        }

        logger.info(
            "[hitem3d.submit] form=%s images=%s multi_images=%s",
            form_fields,
            [(n, len(d), m) for n, d, m in images],
            [(n, len(d), m) for n, d, m in multi_images],
        )

        payload = submit_task(form_fields, images, multi_images)
        data = payload.get("data") or {}
        task_id = data.get("task_id") or data.get("taskId")

        if task_id:
            first = images[0] if images else (multi_images[0] if multi_images else None)
            thumb_url = task_store.save_thumbnail(first[1], first[2]) if first else None
            task_store.create_task(
                user_id=g.current_user["id"],
                task_id=str(task_id),
                thumb_url=thumb_url,
                params=form_fields,
                asset_type="model_3d",
            )
            # Archive the original uploads to OSS so the asset detail view can
            # show them later. This is best-effort: failures don't abort submit.
            all_sources = list(images) + list(multi_images)
            source_keys = _upload_sources(
                g.current_user["id"], str(task_id), all_sources
            )
            if source_keys:
                task_store.update_source_keys(str(task_id), source_keys)
        return _ok(data)
    except Hitem3DError as exc:
        logger.error("[hitem3d.submit] upstream error: %s (code=%s)", exc, exc.code)
        return _err(str(exc), status=exc.code or 1, http_code=exc.status)
    except Exception as exc:  # noqa: BLE001
        logger.error("[hitem3d.submit] server error:\n%s", traceback.format_exc())
        return _err(f"server error: {exc}", http_code=500)


def _maybe_persist_query(task_id: str, data: dict, user_id: str) -> None:
    record = task_store.get_task(task_id)
    if not record:
        return
    state = str(data.get("state") or "").lower() or record.get("state")
    model_url = data.get("url") or data.get("model_url") or record.get("model_url")
    cover_url = data.get("cover_url") or record.get("cover_url")
    task_store.update_task(
        task_id,
        state=state,
        model_url=model_url,
        cover_url=cover_url,
    )
    # Kick off OSS transfer once Hitem3D marks the task successful.
    if task_store.is_terminal(state) and state == "success" and model_url:
        _schedule_oss_upload(user_id, task_id, model_url)


@hitem3d_bp.route("/query", methods=["GET"])
@token_required
def query():
    task_id = (request.args.get("task_id") or "").strip()
    if not task_id:
        return _err("task_id is required")

    try:
        payload = query_task(task_id)
        data = payload.get("data") or {}
        _maybe_persist_query(task_id, data, g.current_user["id"])
        # Replace upstream url with our signed OSS url if already uploaded.
        record = task_store.get_task(task_id)
        signed = _sign_model_url(record or {})
        if signed:
            data = dict(data)
            data["url"] = signed
            data["model_url"] = signed
        elif config.oss_configured() and (record or {}).get("upload_state") != "done":
            data = dict(data)
            data["url"] = None
            data["model_url"] = None
        return _ok(data)
    except Hitem3DError as exc:
        return _err(str(exc), status=exc.code or 1, http_code=exc.status)
    except Exception as exc:  # noqa: BLE001
        return _err(f"server error: {exc}", http_code=500)


@hitem3d_bp.route("/tasks/<task_id>", methods=["DELETE"])
@token_required
def delete_task(task_id: str):
    ok = task_store.delete_task(task_id, g.current_user["id"])
    if not ok:
        return _err("任务不存在", http_code=404)
    return _ok(msg="已删除")


@hitem3d_bp.route("/tasks/<task_id>/sources", methods=["POST"])
@token_required
def upload_task_sources(task_id: str):
    """Supplement original source images for a legacy task.

    Accepts multipart ``images`` (1~N files) and replaces any previously stored
    source images for this task. Ownership is enforced by ``user_id``.
    """
    record = task_store.get_task(task_id)
    if not record:
        return _err("任务不存在", http_code=404)
    if record.get("user_id") != g.current_user["id"]:
        return _err("无权限", http_code=403)
    if not config.oss_configured():
        return _err("OSS 未配置", http_code=500)

    try:
        images = _collect_files("images")
    except Hitem3DError as exc:
        return _err(str(exc), http_code=exc.status or 400)
    if not images:
        return _err("请选择至少一张图片", http_code=400)

    # Best-effort delete previous source objects so we don't leave orphans.
    for old_key in record.get("source_keys") or []:
        try:
            oss_client.delete_object(old_key)
        except Exception:  # noqa: BLE001
            pass

    keys = _upload_sources(g.current_user["id"], task_id, images)
    if not keys:
        return _err("上传失败", http_code=500)
    updated = task_store.update_source_keys(task_id, keys, user_id=g.current_user["id"])
    if not updated:
        return _err("任务不存在", http_code=404)
    return _ok({"source_images": _sign_source_urls(updated)})


@hitem3d_bp.route("/thumb/<name>", methods=["GET"])
def thumb(name: str):
    path = task_store.thumb_path(name)
    if not path:
        return _err("not found", http_code=404)
    return send_file(path)
