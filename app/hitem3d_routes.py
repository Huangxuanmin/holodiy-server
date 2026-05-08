"""Proxy routes for the Hitem3D image-to-3D API."""
from __future__ import annotations

import logging
import traceback
from typing import List, Tuple

from flask import Blueprint, request

from .hitem3d_client import Hitem3DError, query_task, submit_task
from .responses import err as _err, ok as _ok

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


@hitem3d_bp.route("/submit", methods=["POST"])
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
        return _ok(payload.get("data"))
    except Hitem3DError as exc:
        logger.error("[hitem3d.submit] upstream error: %s (code=%s)", exc, exc.code)
        return _err(str(exc), status=exc.code or 1, http_code=exc.status)
    except Exception as exc:  # noqa: BLE001
        logger.error("[hitem3d.submit] server error:\n%s", traceback.format_exc())
        return _err(f"server error: {exc}", http_code=500)


@hitem3d_bp.route("/query", methods=["GET"])
def query():
    task_id = (request.args.get("task_id") or "").strip()
    if not task_id:
        return _err("task_id is required")

    try:
        payload = query_task(task_id)
        return _ok(payload.get("data"))
    except Hitem3DError as exc:
        return _err(str(exc), status=exc.code or 1, http_code=exc.status)
    except Exception as exc:  # noqa: BLE001
        return _err(f"server error: {exc}", http_code=500)
