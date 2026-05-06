"""水平视差 hogel 处理器。"""
import os

import cv2
import numpy as np
from PIL import Image

from .base import HogelProcessor


class HorizontalParallaxProcessor(HogelProcessor):
    """水平视差 hogel 处理器。"""

    def process(self, input_folder, output_folder, C, hogel_width_fixed=500,
                hogel_height_fixed=None, quality=95):
        """
        处理水平视差 hogel 图像。

        参数:
        input_folder: 输入图像文件夹路径
        output_folder: 输出 hogel 图像文件夹路径
        C: hogel 图个数，即每张图像要分割的份数
        hogel_width_fixed: 每个 hogel 的固定像素宽度（默认 500px）
        hogel_height_fixed: 每个 hogel 的固定像素高度（默认 None，表示保持原始高度）
        quality: 输出图像质量（1-100，默认 95）
        """
        # 获取图像文件
        image_files = self.validate_image_folder(input_folder)
        print(f"找到 {len(image_files)} 个图像文件")

        # 读取第一张图像获取尺寸
        first_image_path = os.path.join(input_folder, image_files[0])
        width, height, mode = self.get_image_info(first_image_path)
        print(f"图像尺寸: {width}x{height}, 模式: {mode}")

        if width % C != 0:
            print(f"警告: 图像宽度 {width} 不能被 {C} 整除，将使用整数除法")

        original_part_width = width // C
        resized_part_width = hogel_width_fixed // len(image_files)
        resized_part_height = hogel_height_fixed if hogel_height_fixed is not None else height

        print(f"原始图像每份尺寸: {original_part_width}x{height} 像素")
        print(f"Resize后每份尺寸: {resized_part_width}x{resized_part_height} 像素")
        if hogel_height_fixed is not None:
            print(f"  - 宽度: {hogel_width_fixed}/{len(image_files)} = {resized_part_width}px")
            print(f"  - 高度: {hogel_height_fixed}px (用户指定)")
        else:
            print(f"  - 宽度: {hogel_width_fixed}/{len(image_files)} = {resized_part_width}px")
            print(f"  - 高度: {height}px (保持原始)")
        print(
            f"每个hogel的总尺寸: {resized_part_width * len(image_files)}x{resized_part_height} 像素 "
            f"(应为: {hogel_width_fixed}x{resized_part_height}px)"
        )

        self.create_output_folder(output_folder)

        # 初始化每个 hogel 的空画布（水平排列）
        hogel_images = [
            Image.new(mode, (resized_part_width * len(image_files), resized_part_height))
            for _ in range(C)
        ]

        # 处理每张图像：裁切、resize、粘贴
        for img_idx, filename in enumerate(image_files):
            img_path = os.path.join(input_folder, filename)

            try:
                with Image.open(img_path) as img:
                    if img.size != (width, height):
                        print(f"警告: {filename} 的尺寸 {img.size} 与第一张图像不一致，将跳过")
                        continue

                    for hogel_idx in range(C):
                        x_start = hogel_idx * original_part_width
                        x_end = x_start + original_part_width
                        hogel_part = img.crop((x_start, 0, x_end, height))

                        hogel_part_np = np.array(hogel_part)
                        new_width = resized_part_width
                        new_height = resized_part_height

                        if new_width > 0 and new_height > 0:
                            hogel_part_resized = cv2.resize(
                                hogel_part_np,
                                (new_width, new_height),
                                interpolation=cv2.INTER_LINEAR,
                            )
                            hogel_part_resized_pil = Image.fromarray(hogel_part_resized)
                            x_position = img_idx * resized_part_width
                            hogel_images[hogel_idx].paste(hogel_part_resized_pil, (x_position, 0))
                        else:
                            print(f"警告: resize尺寸无效 ({new_width}x{new_height})，跳过")

            except Exception as e:
                print(f"处理 {filename} 时出错: {e}")

        # 保存所有 hogel 图像（必要时最终 resize 到固定尺寸）
        print(f"\n保存hogel图像到 {output_folder}:")
        for hogel_idx in range(C):
            output_filename = f"hogel_{hogel_idx:03d}.jpg"
            output_path = os.path.join(output_folder, output_filename)

            final_hogel = hogel_images[hogel_idx]
            current_width, current_height = final_hogel.size
            target_width = hogel_width_fixed
            target_height = (
                hogel_height_fixed if hogel_height_fixed is not None else current_height
            )

            need_resize = False
            resize_reason = []

            if current_width != target_width:
                need_resize = True
                resize_reason.append(f"宽度 {current_width}px → {target_width}px")

            if hogel_height_fixed is not None and current_height != target_height:
                need_resize = True
                resize_reason.append(f"高度 {current_height}px → {target_height}px")

            if need_resize:
                final_hogel_np = np.array(final_hogel)
                final_hogel_resized = cv2.resize(
                    final_hogel_np,
                    (target_width, target_height),
                    interpolation=cv2.INTER_LINEAR,
                )
                final_hogel = Image.fromarray(final_hogel_resized)
                reason_str = ", ".join(resize_reason)
                print(
                    f"  已保存: {output_filename} "
                    f"({target_width}x{target_height}) [resized: {reason_str}]"
                )
            else:
                print(f"  已保存: {output_filename} ({current_width}x{current_height})")

            final_hogel.save(output_path, quality=quality)

        print(f"\n处理完成! 共生成 {C} 个hogel图像")
        return C
