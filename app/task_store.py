"""Hitem3D task store backed by SQLAlchemy (SQLite by default).

Public API kept compatible with the previous JSON-based implementation.
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from .config import BASE_DIR
from .db import session_scope
from .models import Hitem3dTask

_THUMB_DIR = os.path.join(BASE_DIR, "uploads", "hitem3d_thumbs")
os.makedirs(_THUMB_DIR, exist_ok=True)

_TERMINAL_STATES = {"success", "failed", "cancelled", "error"}

# Asset categories exposed to the frontend.
ASSET_TYPES = ("model_3d", "parallax", "hogel")
_DEFAULT_ASSET_TYPE = "model_3d"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _to_dict(row: Hitem3dTask) -> Dict[str, Any]:
    return {
        "task_id": row.task_id,
        "user_id": row.user_id,
        "state": row.state,
        "asset_type": row.asset_type or _DEFAULT_ASSET_TYPE,
        "model_url": row.model_url,
        "cover_url": row.cover_url,
        "thumb_url": row.thumb_url,
        "params": dict(row.params or {}),
        "oss_key": row.oss_key,
        "file_size": row.file_size,
        "upload_state": row.upload_state,
        "upload_error": row.upload_error,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def save_thumbnail(image_bytes: bytes, mime: str) -> Optional[str]:
    if not image_bytes:
        return None
    ext = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
    }.get((mime or "").lower(), ".png")
    name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(_THUMB_DIR, name), "wb") as f:
        f.write(image_bytes)
    return f"/api/image-to-3d/thumb/{name}"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_task(
    *,
    user_id: str,
    task_id: str,
    thumb_url: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None,
    asset_type: str = _DEFAULT_ASSET_TYPE,
) -> Dict[str, Any]:
    now = time.time()
    with session_scope() as session:
        row = Hitem3dTask(
            task_id=task_id,
            user_id=user_id,
            state="pending",
            asset_type=asset_type or _DEFAULT_ASSET_TYPE,
            thumb_url=thumb_url,
            params=params or {},
            created_at=now,
            updated_at=now,
        )
        session.merge(row)
        session.flush()
        fresh = session.get(Hitem3dTask, task_id)
        return _to_dict(fresh) if fresh else _to_dict(row)


def update_task(task_id: str, *, state: Optional[str] = None,
                model_url: Optional[str] = None,
                cover_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with session_scope() as session:
        row = session.get(Hitem3dTask, task_id)
        if not row:
            return None
        if state is not None:
            row.state = state
        if model_url is not None:
            row.model_url = model_url
        if cover_url is not None:
            row.cover_url = cover_url
        row.updated_at = time.time()
        session.flush()
        return _to_dict(row)


def update_upload(task_id: str, *, upload_state: Optional[str] = None,
                  oss_key: Optional[str] = None,
                  file_size: Optional[int] = None,
                  upload_error: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Update OSS-upload-related fields on a task record."""
    with session_scope() as session:
        row = session.get(Hitem3dTask, task_id)
        if not row:
            return None
        if upload_state is not None:
            row.upload_state = upload_state
        if oss_key is not None:
            row.oss_key = oss_key
        if file_size is not None:
            row.file_size = file_size
        if upload_error is not None:
            row.upload_error = upload_error
        row.updated_at = time.time()
        session.flush()
        return _to_dict(row)


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    with session_scope() as session:
        row = session.get(Hitem3dTask, task_id)
        return _to_dict(row) if row else None


def list_tasks_for_user(user_id: str, asset_type: Optional[str] = None) -> List[Dict[str, Any]]:
    with session_scope() as session:
        stmt = select(Hitem3dTask).where(Hitem3dTask.user_id == user_id)
        if asset_type:
            stmt = stmt.where(Hitem3dTask.asset_type == asset_type)
        rows = session.scalars(stmt.order_by(Hitem3dTask.created_at.desc())).all()
        return [_to_dict(r) for r in rows]


def delete_task(task_id: str, user_id: str) -> bool:
    with session_scope() as session:
        row = session.get(Hitem3dTask, task_id)
        if not row or row.user_id != user_id:
            return False
        thumb = row.thumb_url
        oss_key = row.oss_key
        session.delete(row)

    # best-effort remove the stored thumbnail
    prefix = "/api/image-to-3d/thumb/"
    if thumb and thumb.startswith(prefix):
        path = os.path.join(_THUMB_DIR, thumb[len(prefix):])
        try:
            if os.path.isfile(path):
                os.remove(path)
        except OSError:
            pass

    # best-effort remove the OSS object (ignored if OSS isn't configured)
    if oss_key:
        try:
            from . import oss_client
            oss_client.delete_object(oss_key)
        except Exception:  # noqa: BLE001
            pass
    return True


def thumb_path(name: str) -> Optional[str]:
    if not name or os.sep in name or "/" in name or "\\" in name or ".." in name:
        return None
    path = os.path.join(_THUMB_DIR, name)
    return path if os.path.isfile(path) else None


def is_terminal(state: str) -> bool:
    return str(state or "").lower() in _TERMINAL_STATES


# ---------------------------------------------------------------------------
# JSON -> SQLite migration (one-shot, idempotent)
# ---------------------------------------------------------------------------

def _migrate_json_to_sqlite() -> None:
    import json

    json_path = os.path.join(BASE_DIR, "data", "hitem3d_tasks.json")
    if not os.path.exists(json_path):
        return
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    if not data:
        return

    with session_scope() as session:
        existing = session.scalar(select(Hitem3dTask).limit(1))
        if existing:
            return
        for tid, rec in data.items():
            session.merge(Hitem3dTask(
                task_id=tid,
                user_id=rec.get("user_id", ""),
                state=rec.get("state") or "pending",
                asset_type=rec.get("asset_type") or _DEFAULT_ASSET_TYPE,
                model_url=rec.get("model_url"),
                cover_url=rec.get("cover_url"),
                thumb_url=rec.get("thumb_url"),
                params=rec.get("params") or {},
                created_at=rec.get("created_at") or time.time(),
                updated_at=rec.get("updated_at") or time.time(),
            ))

    try:
        os.replace(json_path, json_path + ".migrated")
    except OSError:
        pass
