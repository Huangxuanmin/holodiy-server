"""通用工具集。

包含文件名校验、图片压缩（上传 OSS 前统一压缩为 JPEG）、Hogel 阵列拼图、
zip 打包等跨模块复用的辅助函数。
"""
import base64
import io
import os
import re

from PIL import Image
from werkzeug.utils import secure_filename

from .config import ALLOWED_EXTENSIONS


def allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许。"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def compress_image_bytes(
    data: bytes,
    *,
    max_long_edge: int = 1600,
    quality: int = 85,
) -> tuple[bytes, str, str]:
    """Re-encode an image to JPEG with a max long-edge.

    Returns ``(bytes, content_type, extension)``. If Pillow can't decode the
    input, falls back to the original bytes with ``image/octet-stream``.
    """
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            # Flatten alpha against white so the JPEG looks right.
            if img.mode in ("RGBA", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                alpha = img.split()[-1]
                background.paste(img.convert("RGB"), mask=alpha)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            longest = max(img.size)
            if longest > max_long_edge:
                scale = max_long_edge / float(longest)
                new_size = (
                    max(1, int(img.size[0] * scale)),
                    max(1, int(img.size[1] * scale)),
                )
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            return buf.getvalue(), "image/jpeg", ".jpg"
    except Exception:  # noqa: BLE001
        return data, "application/octet-stream", ".bin"


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


_FULL_HOGEL_PATTERN = re.compile(r"hogel_(\d+)_(\d+)\.jpg$", re.IGNORECASE)


def build_composite_image(
    source_dir: str,
    destination_dir: str,
    mode: str,
    output_name: str = "composite.jpg",
    quality: int = 95,
    max_canvas_size: int = 8000,
):
    """将 source_dir 下的 hogel 按规则阵列排列成一张大图保存到 destination_dir。

    mode="horizontal": 按文件名排序，1 行 × N 列 水平拼接。
    mode="full": 解析文件名 hogel_{row}_{col}.jpg, 按 row/col 拼接成二维阵列。

    返回字典 {path, name, width, height, cols, rows, tile_width, tile_height}
    超过 max_canvas_size 会等比缩放保存，避免过大内存/文件。
    """
    files = sorted(
        f for f in os.listdir(source_dir) if f.lower().endswith(".jpg")
    )
    if not files:
        return None

    first_path = os.path.join(source_dir, files[0])
    with Image.open(first_path) as first:
        tile_w, tile_h = first.size
        img_mode = first.mode if first.mode in ("RGB", "RGBA", "L") else "RGB"

    if mode == "full":
        positions = []
        for filename in files:
            match = _FULL_HOGEL_PATTERN.search(filename)
            if match:
                positions.append((int(match.group(1)), int(match.group(2)), filename))
        if not positions:
            return None
        rows = max(r for r, _, _ in positions) + 1
        cols = max(c for _, c, _ in positions) + 1
    else:
        positions = [(0, idx, filename) for idx, filename in enumerate(files)]
        rows = 1
        cols = len(files)

    canvas_w = cols * tile_w
    canvas_h = rows * tile_h

    canvas = Image.new(img_mode, (canvas_w, canvas_h))
    for row, col, filename in positions:
        with Image.open(os.path.join(source_dir, filename)) as tile_img:
            if tile_img.mode != img_mode:
                tile_img = tile_img.convert(img_mode)
            canvas.paste(tile_img, (col * tile_w, row * tile_h))

    # 避免阵列过大，按最长边缩放
    scale = 1.0
    longest = max(canvas_w, canvas_h)
    if longest > max_canvas_size:
        scale = max_canvas_size / longest
        new_size = (max(1, int(canvas_w * scale)), max(1, int(canvas_h * scale)))
        canvas = canvas.resize(new_size, Image.Resampling.LANCZOS)

    os.makedirs(destination_dir, exist_ok=True)
    output_path = os.path.join(destination_dir, output_name)
    canvas.save(output_path, format="JPEG", quality=quality)

    return {
        "path": output_path,
        "name": output_name,
        "width": canvas.width,
        "height": canvas.height,
        "cols": cols,
        "rows": rows,
        "tile_width": tile_w,
        "tile_height": tile_h,
    }


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
