"""全视差 hogel 处理器。"""
import math
import os

from PIL import Image

from .base import HogelProcessor


class FullParallaxProcessor(HogelProcessor):
    """全视差 hogel 处理器。"""

    def calculate_optimal_grid(self, total_tiles):
        """计算最接近 1:1 的网格布局。

        返回 (grid_size, used_tiles)：
        - grid_size: 每行/每列的小方块数
        - used_tiles: 实际使用的小方块数量
        """
        grid_size = int(math.sqrt(total_tiles))
        while grid_size > 0:
            if total_tiles >= grid_size * grid_size:
                return grid_size, grid_size * grid_size
            grid_size -= 1
        return 1, 1

    def process(self, input_folder, output_folder, canvas_width, canvas_height,
                exposure_width, quality=95):
        """
        处理全视差图像生成 hogel。

        参数:
        input_folder: 输入图像文件夹路径
        output_folder: 输出 hogel 图像文件夹路径
        canvas_width: 画幅宽度（mm）
        canvas_height: 画幅高度（mm）
        exposure_width: 曝光宽度（mm）
        quality: 输出图像质量（1-100，默认 95）
        """
        image_files = self.validate_image_folder(input_folder)
        print(f"找到 {len(image_files)} 个图像文件")

        first_image_path = os.path.join(input_folder, image_files[0])
        img_width, img_height, mode = self.get_image_info(first_image_path)
        print(f"图像尺寸: {img_width}x{img_height}, 模式: {mode}")

        # 计算 C（每张图像分割的份数）
        C = canvas_width / exposure_width
        if C <= 0:
            raise ValueError(
                f"C必须大于0 (canvas_width={canvas_width}, exposure_width={exposure_width})"
            )
        C = int(C)
        if C <= 0:
            raise ValueError(f"C必须是正整数，当前C={C}")

        print(f"\n计算参数:")
        print(f"  画幅宽度: {canvas_width}mm")
        print(f"  画幅高度: {canvas_height}mm")
        print(f"  曝光宽度: {exposure_width}mm")
        print(f"  分割份数 C: {C} (每张图像将被分割成{C}×{C}个小方块)")

        tile_width = img_width // C
        tile_height = img_height // C

        print(f"  每个小方块尺寸: {tile_width}x{tile_height} 像素")
        print(f"  每张图像总小方块数: {C}×{C} = {C * C} 个")

        if img_width % C != 0 or img_height % C != 0:
            print(f"警告: 图像尺寸 {img_width}x{img_height} 不能被 {C} 整除，将使用整数除法")
            print(f"  实际小方块尺寸: {tile_width}x{tile_height} 像素")

        total_tiles_per_position = len(image_files)
        print(f"  每个位置的小方块数量: {total_tiles_per_position} (来自{len(image_files)}张图像)")

        grid_size, used_tiles = self.calculate_optimal_grid(total_tiles_per_position)
        print(f"  最优网格布局: {grid_size}×{grid_size} = {used_tiles} 个小方块")

        if used_tiles < total_tiles_per_position:
            print(
                f"  注意: 将使用前 {used_tiles} 个小方块，"
                f"舍弃 {total_tiles_per_position - used_tiles} 个"
            )

        self.create_output_folder(output_folder)

        total_hogels = C * C
        print(f"\n开始处理 {total_hogels} 个hogel图像...")

        # 为每个位置创建空白 hogel 图像
        hogel_img_width = tile_width * grid_size
        hogel_img_height = tile_height * grid_size
        hogel_images = [
            Image.new(mode, (hogel_img_width, hogel_img_height))
            for _ in range(total_hogels)
        ]

        # 遍历每张图像，将其切成 C×C 的小方块并粘贴到对应 hogel 画布的网格位置
        for img_idx, filename in enumerate(image_files):
            if img_idx >= used_tiles:
                print(f"  跳过图像 {filename} (超出使用的{used_tiles}个小方块限制)")
                continue

            img_path = os.path.join(input_folder, filename)

            try:
                with Image.open(img_path) as img:
                    if img.size != (img_width, img_height):
                        print(f"警告: {filename} 的尺寸 {img.size} 与第一张图像不一致，将跳过")
                        continue

                    grid_row = img_idx // grid_size
                    grid_col = img_idx % grid_size

                    for row in range(C):
                        for col in range(C):
                            hogel_idx = row * C + col

                            x_start = col * tile_width
                            y_start = row * tile_height
                            x_end = x_start + tile_width
                            y_end = y_start + tile_height
                            tile = img.crop((x_start, y_start, x_end, y_end))

                            tile_x = grid_col * tile_width
                            tile_y = grid_row * tile_height
                            hogel_images[hogel_idx].paste(tile, (tile_x, tile_y))

                    print(f"  已处理: {filename} → 网格位置 ({grid_row},{grid_col})")

            except Exception as e:
                print(f"处理 {filename} 时出错: {e}")

        # 保存所有 hogel 图像
        print(f"\n保存hogel图像到 {output_folder}:")
        for row in range(C):
            for col in range(C):
                hogel_idx = row * C + col
                hogel_img = hogel_images[hogel_idx]

                output_filename = f"hogel_{row:03d}_{col:03d}.jpg"
                output_path = os.path.join(output_folder, output_filename)
                hogel_img.save(output_path, quality=quality)

                w, h = hogel_img.size
                print(f"  已保存: {output_filename} ({w}x{h}) - 位置 ({row},{col})")

        print("\n处理完成!")
        print(f"  共生成 {total_hogels} 个hogel图像")
        print(f"  每个hogel尺寸: {hogel_img_width}x{hogel_img_height} 像素")
        print(f"  网格布局: {grid_size}×{grid_size} 个小方块")
        print(f"  输出文件夹: {output_folder}")

        return total_hogels
