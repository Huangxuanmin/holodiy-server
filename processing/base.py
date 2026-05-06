"""Hogel 处理器基类。"""
import os

from PIL import Image


class HogelProcessor:
    """Hogel 图像处理器基类，封装通用的文件校验和元信息读取。"""

    def __init__(self):
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp'}

    def validate_image_folder(self, input_folder):
        """验证输入文件夹并返回已排序的图像文件名列表。"""
        if not os.path.exists(input_folder):
            raise ValueError(f"输入文件夹不存在: {input_folder}")

        image_files = []
        for f in os.listdir(input_folder):
            ext = os.path.splitext(f)[1].lower()
            if ext in self.supported_formats:
                image_files.append(f)

        if not image_files:
            raise ValueError(f"在文件夹 {input_folder} 中没有找到支持的图像文件")

        image_files.sort()
        return image_files

    def get_image_info(self, image_path):
        """获取图像的宽、高、模式。"""
        with Image.open(image_path) as img:
            return img.size[0], img.size[1], img.mode

    def create_output_folder(self, output_folder):
        """创建输出文件夹（存在则忽略）。"""
        os.makedirs(output_folder, exist_ok=True)
        return output_folder
