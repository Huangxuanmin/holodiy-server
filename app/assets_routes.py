"""资产库统一列表路由。

对外只暴露一个 ``GET /api/assets/list`` 接口，支持通过 ``type`` 查询参数
按资产类型（``model_3d`` / ``parallax`` / ``hogel``）过滤，不传则返回全部。

兼职两件事：
1. 对未结束的 3D 任务，实时向 Hitem3D 上游查询最新状态并写回本地库；
2. 对已完成但 OSS 还未上传 / 上传失败的任务，自动补发 OSS 转存任务。
"""
from __future__ import annotations

from flask import Blueprint, g, request

from . import task_store
from .auth_routes import token_required
from .hitem3d_client import Hitem3DError, query_task
from .hitem3d_routes import (
    _maybe_persist_query,
    _schedule_oss_upload,
    _shape_record,
)
from .responses import err as _err, ok as _ok

assets_bp = Blueprint("assets", __name__, url_prefix="/api/assets")


@assets_bp.route("/list", methods=["GET"])
@token_required
def list_assets():
    """List current user's assets, optionally filtered by ``type``.

    Query params:
        type: one of ``model_3d`` / ``parallax`` / ``hogel``. Omit for all.
    """
    user_id = g.current_user["id"]
    asset_type = (request.args.get("type") or "").strip() or None
    if asset_type and asset_type not in task_store.ASSET_TYPES:
        return _err(f"invalid type: {asset_type}")

    items = task_store.list_tasks_for_user(user_id, asset_type=asset_type)
    updated_any = False
    for item in items:
        # Only 3D-model tasks are backed by the Hitem3D upstream; skip the rest.
        if item.get("asset_type") != "model_3d":
            continue
        # 1) sync non-terminal tasks from upstream
        if not task_store.is_terminal(item.get("state", "")):
            try:
                payload = query_task(item["task_id"])
            except Hitem3DError:
                continue
            data = payload.get("data") or {}
            _maybe_persist_query(item["task_id"], data, user_id)
            updated_any = True
        # 2) re-try OSS upload for success-but-not-yet-uploaded / previously failed jobs
        elif item.get("state") == "success" and item.get("upload_state") != "done" \
                and item.get("model_url"):
            _schedule_oss_upload(user_id, item["task_id"], item["model_url"])

    if updated_any:
        items = task_store.list_tasks_for_user(user_id, asset_type=asset_type)

    items = [_shape_record(item) for item in items]
    return _ok({"items": items})
