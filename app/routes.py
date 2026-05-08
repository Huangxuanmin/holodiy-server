"""Hogel 图像处理服务的业务路由。

提供视差图 / Hogel 阵列生成、上传、预览、打包下载等能力，和 Hitem3D 的
3D 模型路由相互独立。
"""
import os
import shutil
import tempfile
import uuid
from typing import Optional

from flask import Blueprint, current_app, request, send_file
from werkzeug.utils import secure_filename

from processing import create_processor

from .responses import err as _err, ok as _ok
from .utils import (
    allowed_file,
    build_composite_image,
    build_hogel_zip,
    get_image_preview,
    safe_task_subdir,
    save_request_files_to_dir,
)

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

def _get_task_upload_dir(task_id: str):
    return safe_task_subdir(current_app.config["UPLOAD_FOLDER"], task_id)


def _get_task_output_dir(task_id: str):
    return safe_task_subdir(current_app.config["OUTPUT_FOLDER"], task_id)


def _prepare_input_files(temp_input_dir: str):
    """根据请求准备输入图像到临时目录，返回错误响应或 None。"""
    task_id = request.form.get("taskId", type=str, default="").strip()
    if task_id:
        _, task_upload_dir = _get_task_upload_dir(task_id)
        if not os.path.isdir(task_upload_dir):
            return _err(f"任务不存在: {task_id}")

        copied_count = 0
        for filename in os.listdir(task_upload_dir):
            source_path = os.path.join(task_upload_dir, filename)
            if not os.path.isfile(source_path) or not allowed_file(filename):
                continue
            shutil.copy2(source_path, os.path.join(temp_input_dir, filename))
            copied_count += 1

        if copied_count == 0:
            return _err(f"任务 {task_id} 下没有有效图像文件")
        return None

    if "files" not in request.files:
        return _err("没有文件上传")

    files = request.files.getlist("files")
    if not files:
        return _err("没有选择文件")

    saved_files = save_request_files_to_dir(files, temp_input_dir)
    if not saved_files:
        return _err("没有有效的图像文件")

    return None


def _collect_generated_hogels(
    task_id: str,
    temp_output_dir: str,
    filename_prefix: str,
    composite_mode: Optional[str] = None,
):
    safe_task_id, task_output_dir = _get_task_output_dir(task_id)
    os.makedirs(task_output_dir, exist_ok=True)

    hogel_files = sorted(
        f for f in os.listdir(temp_output_dir) if f.lower().endswith(".jpg")
    )

    hogels = []
    for hogel_file in hogel_files:
        hogel_path = os.path.join(temp_output_dir, hogel_file)
        preview_url = get_image_preview(hogel_path)
        file_size = os.path.getsize(hogel_path)

        output_filename = f"{filename_prefix}_{len(hogels) + 1:03d}.jpg"
        output_path = os.path.join(task_output_dir, output_filename)
        shutil.copy2(hogel_path, output_path)

        hogels.append(
            {
                "name": output_filename,
                "size": f"{file_size / 1024:.1f} KB",
                "preview_url": preview_url,
                "download_url": f"/api/download/{safe_task_id}/{output_filename}",
            }
        )

    composite = None
    if composite_mode and hogels:
        try:
            composite_name = f"{filename_prefix}_composite.jpg"
            info = build_composite_image(
                source_dir=temp_output_dir,
                destination_dir=task_output_dir,
                mode=composite_mode,
                output_name=composite_name,
            )
            if info:
                composite_preview = get_image_preview(
                    info["path"], max_size=(1600, 1600)
                )
                composite_size = os.path.getsize(info["path"])
                composite = {
                    "name": info["name"],
                    "size": f"{composite_size / 1024:.1f} KB",
                    "preview_url": composite_preview,
                    "download_url": f"/api/download/{safe_task_id}/{info['name']}",
                    "width": info["width"],
                    "height": info["height"],
                    "cols": info["cols"],
                    "rows": info["rows"],
                }
        except Exception as exc:
            print(f"生成合成预览图失败: {exc}")

    download_all_url = f"/api/download-all/{safe_task_id}" if hogels else None
    return hogels, download_all_url, composite


def _resolve_generation_task_id() -> str:
    task_id = request.form.get("taskId", type=str, default="").strip()
    return task_id or uuid.uuid4().hex


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@api_bp.route("/health", methods=["GET"])
def health_check():
    """健康检查端点。"""
    return _ok({"healthy": True}, msg="Hogel API 服务运行正常")


@api_bp.route("/upload", methods=["POST"])
def upload_files():
    """上传文件接口。"""
    if "files" not in request.files:
        return _err("没有文件上传")

    files = request.files.getlist("files")
    if not files:
        return _err("没有选择文件")

    requested_task_id = request.form.get("taskId", type=str, default="").strip()
    task_id = requested_task_id or uuid.uuid4().hex
    safe_task_id, task_upload_dir = _get_task_upload_dir(task_id)
    if not safe_task_id:
        safe_task_id = uuid.uuid4().hex
        _, task_upload_dir = _get_task_upload_dir(safe_task_id)

    os.makedirs(task_upload_dir, exist_ok=True)
    saved_files = save_request_files_to_dir(files, task_upload_dir)
    if not saved_files:
        return _err("没有有效的图像文件")

    uploaded_files = []
    for file_path in saved_files:
        uploaded_files.append(
            {
                "filename": os.path.basename(file_path),
                "size": os.path.getsize(file_path),
                "preview_url": get_image_preview(file_path),
                "path": file_path,
            }
        )

    return _ok(
        {
            "taskId": safe_task_id,
            "files": uploaded_files,
        },
        msg=f"成功上传 {len(uploaded_files)} 个文件",
    )


@api_bp.route("/generate-hogel", methods=["POST"])
def generate_hogel():
    """生成 hogel 图像接口（水平视差）。"""
    try:
        C = request.form.get("C", type=int, default=10)
        width = request.form.get("width", type=int, default=500)
        height = request.form.get("height", type=int, default=None)
        quality = request.form.get("quality", type=int, default=95)

        with tempfile.TemporaryDirectory() as temp_input_dir, tempfile.TemporaryDirectory() as temp_output_dir:
            prepare_error = _prepare_input_files(temp_input_dir)
            if prepare_error:
                return prepare_error

            try:
                processor = create_processor("horizontal")
                processor.process(
                    input_folder=temp_input_dir,
                    output_folder=temp_output_dir,
                    C=C,
                    hogel_width_fixed=width,
                    hogel_height_fixed=height if height else None,
                    quality=quality,
                )
            except Exception as exc:
                return _err(f"处理失败: {exc}", http_code=500)

            task_id = _resolve_generation_task_id()
            hogels, download_all_url, composite = _collect_generated_hogels(
                task_id, temp_output_dir, "hogel_horizontal", composite_mode="horizontal"
            )

            return _ok(
                {
                    "taskId": secure_filename(task_id),
                    "hogels": hogels,
                    "composite": composite,
                    "download_all_url": download_all_url,
                    "log": "水平视差处理成功完成",
                },
                msg=f"成功生成 {len(hogels)} 个水平视差hogel图像",
            )
    except Exception as exc:
        print(f"生成hogel时出错: {exc}")
        return _err(f"服务器内部错误: {exc}", http_code=500)


@api_bp.route("/generate-full-parallax-hogel", methods=["POST"])
def generate_full_parallax_hogel():
    """生成全视差 hogel 图像接口。"""
    try:
        canvas_width = request.form.get("canvas_width", type=float, default=100.0)
        canvas_height = request.form.get("canvas_height", type=float, default=100.0)
        exposure_width = request.form.get("exposure_width", type=float, default=10.0)
        quality = request.form.get("quality", type=int, default=95)

        if canvas_width <= 0 or canvas_height <= 0 or exposure_width <= 0:
            return _err("画幅尺寸和曝光宽度必须大于0")

        if exposure_width > canvas_width:
            return _err("曝光宽度不能大于画幅宽度")

        with tempfile.TemporaryDirectory() as temp_input_dir, tempfile.TemporaryDirectory() as temp_output_dir:
            prepare_error = _prepare_input_files(temp_input_dir)
            if prepare_error:
                return prepare_error

            try:
                processor = create_processor("full")
                processor.process(
                    input_folder=temp_input_dir,
                    output_folder=temp_output_dir,
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                    exposure_width=exposure_width,
                    quality=quality,
                )
            except Exception as exc:
                return _err(f"处理失败: {exc}", http_code=500)

            task_id = _resolve_generation_task_id()
            hogels, download_all_url, composite = _collect_generated_hogels(
                task_id, temp_output_dir, "hogel_full", composite_mode="full"
            )

            return _ok(
                {
                    "taskId": secure_filename(task_id),
                    "hogels": hogels,
                    "composite": composite,
                    "download_all_url": download_all_url,
                    "log": "全视差处理成功完成",
                },
                msg=f"成功生成 {len(hogels)} 个全视差hogel图像",
            )
    except Exception as exc:
        print(f"生成全视差hogel时出错: {exc}")
        return _err(f"服务器内部错误: {exc}", http_code=500)


@api_bp.route("/download/<task_id>/<filename>", methods=["GET"])
def download_task_file(task_id, filename):
    """下载指定任务下的单个文件。"""
    try:
        safe_task_id = secure_filename(task_id)
        safe_filename = secure_filename(filename)
        file_path = os.path.join(
            current_app.config["OUTPUT_FOLDER"], safe_task_id, safe_filename
        )
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        return _err("文件不存在", http_code=404)
    except Exception as exc:
        return _err(str(exc), http_code=500)


@api_bp.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    """下载文件接口（兼容旧路径）。"""
    try:
        safe_filename = secure_filename(filename)
        file_path = os.path.join(current_app.config["OUTPUT_FOLDER"], safe_filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        return _err("文件不存在", http_code=404)
    except Exception as exc:
        return _err(str(exc), http_code=500)


@api_bp.route("/download-all/<task_id>", methods=["GET"])
def download_all_for_task(task_id):
    """下载指定任务的全部 hogel（zip）。"""
    try:
        safe_task_id, task_output_dir = _get_task_output_dir(task_id)
        if not safe_task_id or not os.path.isdir(task_output_dir):
            return _err(f"任务不存在: {task_id}", http_code=404)
        return build_hogel_zip(task_output_dir, f"hogel_{safe_task_id}.zip")
    except Exception as exc:
        return _err(str(exc), http_code=500)


@api_bp.route("/download-all", methods=["GET"])
def download_all():
    """下载所有 hogel 文件（打包为 zip，兼容旧路径）。"""
    try:
        task_id = request.args.get("taskId", "").strip()
        if task_id:
            safe_task_id, task_output_dir = _get_task_output_dir(task_id)
            if not safe_task_id or not os.path.isdir(task_output_dir):
                return _err(f"任务不存在: {task_id}", http_code=404)
            return build_hogel_zip(task_output_dir, f"hogel_{safe_task_id}.zip")
        return build_hogel_zip(current_app.config["OUTPUT_FOLDER"], "hogel_images.zip")
    except Exception as exc:
        return _err(str(exc), http_code=500)


@api_bp.route("/clear-outputs", methods=["POST"])
def clear_outputs():
    """清空输出目录。"""
    try:
        output_folder = current_app.config["OUTPUT_FOLDER"]
        for entry in os.listdir(output_folder):
            entry_path = os.path.join(output_folder, entry)
            if os.path.isfile(entry_path):
                os.remove(entry_path)
            elif os.path.isdir(entry_path):
                shutil.rmtree(entry_path, ignore_errors=True)
        return _ok(msg="输出目录已清空")
    except Exception as exc:
        return _err(str(exc), http_code=500)


@api_bp.route("/settings", methods=["GET"])
def get_default_settings():
    """获取默认设置。"""
    return _ok(
        {
            "horizontal": {
                "hogelCount": 10,
                "hogelWidth": 500,
                "heightMode": "fixed",
                "hogelHeight": 500,
                "quality": 95,
                "enableAntiAliasing": True,
                "enableOptimization": True,
            },
            "full": {
                "canvasWidth": 100.0,
                "canvasHeight": 100.0,
                "exposureWidth": 10.0,
                "quality": 95,
            },
        }
    )


@api_bp.route("/estimate", methods=["POST"])
def estimate_processing():
    """预估处理性能。"""
    try:
        data = request.json or {}
        file_count = data.get("fileCount", 0)
        total_size = data.get("totalSize", 0)  # bytes

        processing_time = max(2, round(file_count * 0.5 + total_size / (1024 * 1024) * 0.1))
        memory_usage = round(total_size / (1024 * 1024) * 1.5)
        output_size = round(total_size * 0.8 / (1024 * 1024))

        return _ok(
            {
                "processingTime": f"~{processing_time}s",
                "memoryUsage": f"~{memory_usage}MB",
                "outputSize": f"~{output_size}MB",
            }
        )
    except Exception as exc:
        return _err(str(exc), http_code=500)
