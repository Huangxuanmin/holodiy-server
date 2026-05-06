"""Helper utilities for file handling and image preview generation."""
import base64
import io
import os

from PIL import Image
from werkzeug.utils import secure_filename

from .config import ALLOWED_EXTENSIONS


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许。"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_image_preview(image_path: str, max_size=(200, 200)):
    """生成图像的 base64 预览图。"""
    try:
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(
                    img, mask=img.split()[-1] if img.mode == "RGBA" else None
                )
                img = background

            img.thumbnail(max_size, Image.Resampling.LANCZOS)

            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/jpeg;base64,{img_str}"
    except Exception as exc:
        print(f"生成预览图失败: {exc}")
        return None


def save_request_files_to_dir(files, target_dir: str):
    """将上传的文件保存到目标目录。"""
    saved_files = []
    for index, file in enumerate(files, start=1):
        if not file or not allowed_file(file.filename):
            continue

        filename = secure_filename(file.filename)
        unique_filename = f"{index:03d}_{filename}"
        file_path = os.path.join(target_dir, unique_filename)
        file.save(file_path)
        saved_files.append(file_path)

    return saved_files


def safe_task_subdir(base_dir: str, task_id: str):
    """返回 (safe_task_id, 对应的子目录绝对路径)。"""
    safe_task_id = secure_filename(task_id)
    return safe_task_id, os.path.join(base_dir, safe_task_id)


def build_hogel_zip(source_dir: str, download_name: str):
    """将指定目录下的 jpg 文件打包成内存中的 zip 并返回 Flask 响应。"""
    import zipfile
    from io import BytesIO

    from flask import send_file

    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in sorted(os.listdir(source_dir)):
            file_path = os.path.join(source_dir, filename)
            if os.path.isfile(file_path) and filename.lower().endswith(".jpg"):
                zf.write(file_path, filename)

    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name=download_name,
    )
