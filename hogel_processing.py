import os
import sys
import math
from PIL import Image
import numpy as np
import cv2

class HogelProcessor:
    """Hogel图像处理器基类"""
    
    def __init__(self):
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp'}
    
    def validate_image_folder(self, input_folder):
        """验证输入文件夹中的图像文件"""
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
        """获取图像信息"""
        with Image.open(image_path) as img:
            width, height = img.size
            mode = img.mode
            return width, height, mode
    
    def create_output_folder(self, output_folder):
        """创建输出文件夹"""
        os.makedirs(output_folder, exist_ok=True)
        return output_folder

class HorizontalParallaxProcessor(HogelProcessor):
    """水平视差hogel处理器"""
    
    def process(self, input_folder, output_folder, C, hogel_width_fixed=500, 
                hogel_height_fixed=None, quality=95):
        """
        处理水平视差hogel图像
        
        参数:
        input_folder: 输入图像文件夹路径
        output_folder: 输出hogel图像文件夹路径
        C: hogel图个数，即每张图像要分割的份数
        hogel_width_fixed: 每个hogel的固定像素宽度（默认500px）
        hogel_height_fixed: 每个hogel的固定像素高度（默认None，表示保持原始高度）
        quality: 输出图像质量（1-100，默认95）
        """
        
        # 获取图像文件
        image_files = self.validate_image_folder(input_folder)
        print(f"找到 {len(image_files)} 个图像文件")
        
        # 读取第一张图像获取尺寸
        first_image_path = os.path.join(input_folder, image_files[0])
        width, height, mode = self.get_image_info(first_image_path)
        print(f"图像尺寸: {width}x{height}, 模式: {mode}")
        
        # 检查宽度是否能被C整除
        if width % C != 0:
            print(f"警告: 图像宽度 {width} 不能被 {C} 整除，将使用整数除法")
        
        # 计算原始图像每份的宽度和resize后的尺寸
        original_part_width = width // C
        resized_part_width = hogel_width_fixed // len(image_files)  # width ÷ 图像数量
        resized_part_height = hogel_height_fixed if hogel_height_fixed is not None else height
        
        print(f"原始图像每份尺寸: {original_part_width}x{height} 像素")
        print(f"Resize后每份尺寸: {resized_part_width}x{resized_part_height} 像素")
        if hogel_height_fixed is not None:
            print(f"  - 宽度: {hogel_width_fixed}/{len(image_files)} = {resized_part_width}px")
            print(f"  - 高度: {hogel_height_fixed}px (用户指定)")
        else:
            print(f"  - 宽度: {hogel_width_fixed}/{len(image_files)} = {resized_part_width}px")
            print(f"  - 高度: {height}px (保持原始)")
        print(f"每个hogel的总尺寸: {resized_part_width * len(image_files)}x{resized_part_height} 像素 (应为: {hogel_width_fixed}x{resized_part_height}px)")
        
        # 创建输出文件夹
        self.create_output_folder(output_folder)
        
        # 初始化hogel图像列表
        hogel_images = []
        for i in range(C):
            # 创建空白图像用于存储第i个hogel（水平排列）
            hogel_img = Image.new(mode, (resized_part_width * len(image_files), resized_part_height))
            hogel_images.append(hogel_img)
        
        # 处理每张图像
        for img_idx, filename in enumerate(image_files):
            img_path = os.path.join(input_folder, filename)
            
            try:
                with Image.open(img_path) as img:
                    # 确保图像尺寸一致
                    if img.size != (width, height):
                        print(f"警告: {filename} 的尺寸 {img.size} 与第一张图像不一致，将跳过")
                        continue
                    
                    # 将图像分割成C份
                    for hogel_idx in range(C):
                        # 计算当前hogel的x坐标范围
                        x_start = hogel_idx * original_part_width
                        x_end = x_start + original_part_width
                        
                        # 裁剪当前hogel部分
                        hogel_part = img.crop((x_start, 0, x_end, height))
                        
                        # 使用OpenCV进行resize（同时调整宽度和高度）
                        # 将PIL图像转换为numpy数组
                        hogel_part_np = np.array(hogel_part)
                        
                        # 计算resize后的尺寸
                        new_width = resized_part_width
                        new_height = resized_part_height
                        
                        # 使用OpenCV resize
                        if new_width > 0 and new_height > 0:
                            hogel_part_resized = cv2.resize(
                                hogel_part_np, 
                                (new_width, new_height), 
                                interpolation=cv2.INTER_LINEAR
                            )
                            
                            # 将numpy数组转换回PIL图像
                            hogel_part_resized_pil = Image.fromarray(hogel_part_resized)
                            
                            # 将resize后的部分粘贴到对应的hogel图像中（水平排列）
                            x_position = img_idx * resized_part_width
                            hogel_images[hogel_idx].paste(hogel_part_resized_pil, (x_position, 0))
                        else:
                            print(f"警告: resize尺寸无效 ({new_width}x{new_height})，跳过")
                        
            except Exception as e:
                print(f"处理 {filename} 时出错: {e}")
        
        # 保存所有hogel图像（可选：最终resize到固定宽度）
        print(f"\n保存hogel图像到 {output_folder}:")
        for hogel_idx in range(C):
            output_filename = f"hogel_{hogel_idx:03d}.jpg"
            output_path = os.path.join(output_folder, output_filename)
            
            # 如果需要将最终hogel resize到固定尺寸
            final_hogel = hogel_images[hogel_idx]
            current_width, current_height = final_hogel.size
            
            target_width = hogel_width_fixed
            target_height = hogel_height_fixed if hogel_height_fixed is not None else current_height
            
            need_resize = False
            resize_reason = []
            
            if current_width != target_width:
                need_resize = True
                resize_reason.append(f"宽度 {current_width}px → {target_width}px")
            
            if hogel_height_fixed is not None and current_height != target_height:
                need_resize = True
                resize_reason.append(f"高度 {current_height}px → {target_height}px")
            
            if need_resize:
                # 将hogel图像resize到目标尺寸
                new_width = target_width
                new_height = target_height
                
                # 使用OpenCV进行resize
                final_hogel_np = np.array(final_hogel)
                final_hogel_resized = cv2.resize(
                    final_hogel_np,
                    (new_width, new_height),
                    interpolation=cv2.INTER_LINEAR
                )
                final_hogel = Image.fromarray(final_hogel_resized)
                reason_str = ", ".join(resize_reason)
                print(f"  已保存: {output_filename} ({new_width}x{new_height}) [resized: {reason_str}]")
            else:
                print(f"  已保存: {output_filename} ({current_width}x{current_height})")
            
            final_hogel.save(output_path, quality=quality)
        
        print(f"\n处理完成! 共生成 {C} 个hogel图像")
        return C

class FullParallaxProcessor(HogelProcessor):
    """全视差hogel处理器"""
    
    def calculate_optimal_grid(self, total_tiles):
        """
        计算最接近的1:1网格布局
        
        参数:
        total_tiles: 总的小方块数量
        
        返回:
        grid_size: 网格大小（每行/每列的小方块数）
        used_tiles: 实际使用的小方块数量
        """
        # 找到最接近的平方数
        grid_size = int(math.sqrt(total_tiles))
        
        # 检查是否可以形成完整的网格
        while grid_size > 0:
            if total_tiles >= grid_size * grid_size:
                used_tiles = grid_size * grid_size
                return grid_size, used_tiles
            grid_size -= 1
        
        # 如果找不到合适的网格，至少使用1×1
        return 1, 1
    
    def process(self, input_folder, output_folder, canvas_width, canvas_height, 
                exposure_width, quality=95):
        """
        处理全视差图像生成hogel
        
        参数:
        input_folder: 输入图像文件夹路径
        output_folder: 输出hogel图像文件夹路径
        canvas_width: 画幅宽度（mm）
        canvas_height: 画幅高度（mm）
        exposure_width: 曝光宽度（mm）
        quality: 输出图像质量（1-100，默认95）
        """
        
        # 获取图像文件
        image_files = self.validate_image_folder(input_folder)
        print(f"找到 {len(image_files)} 个图像文件")
        
        # 读取第一张图像获取尺寸
        first_image_path = os.path.join(input_folder, image_files[0])
        img_width, img_height, mode = self.get_image_info(first_image_path)
        print(f"图像尺寸: {img_width}x{img_height}, 模式: {mode}")
        
        # 计算C（每张图像分割的份数）
        C = canvas_width / exposure_width
        if C <= 0:
            raise ValueError(f"C必须大于0 (canvas_width={canvas_width}, exposure_width={exposure_width})")
        
        # 确保C是整数
        C = int(C)
        if C <= 0:
            raise ValueError(f"C必须是正整数，当前C={C}")
        
        print(f"\n计算参数:")
        print(f"  画幅宽度: {canvas_width}mm")
        print(f"  画幅高度: {canvas_height}mm")
        print(f"  曝光宽度: {exposure_width}mm")
        print(f"  分割份数 C: {C} (每张图像将被分割成{C}×{C}个小方块)")
        
        # 计算每个小方块的尺寸
        tile_width = img_width // C
        tile_height = img_height // C
        
        print(f"  每个小方块尺寸: {tile_width}x{tile_height} 像素")
        print(f"  每张图像总小方块数: {C}×{C} = {C*C} 个")
        
        # 检查图像尺寸是否能被C整除
        if img_width % C != 0 or img_height % C != 0:
            print(f"警告: 图像尺寸 {img_width}x{img_height} 不能被 {C} 整除，将使用整数除法")
            print(f"  实际小方块尺寸: {tile_width}x{tile_height} 像素")
        
        # 计算总的小方块数量
        total_tiles_per_position = len(image_files)
        print(f"  每个位置的小方块数量: {total_tiles_per_position} (来自{len(image_files)}张图像)")
        
        # 计算最优的网格布局
        grid_size, used_tiles = self.calculate_optimal_grid(total_tiles_per_position)
        print(f"  最优网格布局: {grid_size}×{grid_size} = {used_tiles} 个小方块")
        
        if used_tiles < total_tiles_per_position:
            print(f"  注意: 将使用前 {used_tiles} 个小方块，舍弃 {total_tiles_per_position - used_tiles} 个")
        
        # 创建输出文件夹
        self.create_output_folder(output_folder)
        
        # 初始化hogel图像列表
        # 总共有 C×C 个hogel（每个位置一个）
        total_hogels = C * C
        hogel_images = []
        
        print(f"\n开始处理 {total_hogels} 个hogel图像...")
        
        # 为每个位置创建空白hogel图像
        for hogel_idx in range(total_hogels):
            # 计算hogel图像的尺寸
            hogel_img_width = tile_width * grid_size
            hogel_img_height = tile_height * grid_size
            
            # 创建空白图像
            hogel_img = Image.new(mode, (hogel_img_width, hogel_img_height))
            hogel_images.append(hogel_img)
        
        # 处理每张图像
        for img_idx, filename in enumerate(image_files):
            if img_idx >= used_tiles:
                print(f"  跳过图像 {filename} (超出使用的{used_tiles}个小方块限制)")
                continue
                
            img_path = os.path.join(input_folder, filename)
            
            try:
                with Image.open(img_path) as img:
                    # 确保图像尺寸一致
                    if img.size != (img_width, img_height):
                        print(f"警告: {filename} 的尺寸 {img.size} 与第一张图像不一致，将跳过")
                        continue
                    
                    # 计算当前图像在网格中的位置
                    grid_row = img_idx // grid_size
                    grid_col = img_idx % grid_size
                    
                    # 将图像分割成C×C个小方块
                    for row in range(C):
                        for col in range(C):
                            # 计算当前小方块在图像中的位置
                            hogel_idx = row * C + col
                            
                            # 计算裁剪区域
                            x_start = col * tile_width
                            y_start = row * tile_height
                            x_end = x_start + tile_width
                            y_end = y_start + tile_height
                            
                            # 裁剪小方块
                            tile = img.crop((x_start, y_start, x_end, y_end))
                            
                            # 计算小方块在hogel图像中的位置
                            tile_x = grid_col * tile_width
                            tile_y = grid_row * tile_height
                            
                            # 将小方块粘贴到对应的hogel图像中
                            hogel_images[hogel_idx].paste(tile, (tile_x, tile_y))
                    
                    print(f"  已处理: {filename} → 网格位置 ({grid_row},{grid_col})")
                    
            except Exception as e:
                print(f"处理 {filename} 时出错: {e}")
        
        # 保存所有hogel图像
        print(f"\n保存hogel图像到 {output_folder}:")
        
        for row in range(C):
            for col in range(C):
                hogel_idx = row * C + col
                hogel_img = hogel_images[hogel_idx]
                
                # 生成文件名
                output_filename = f"hogel_{row:03d}_{col:03d}.jpg"
                output_path = os.path.join(output_folder, output_filename)
                
                # 保存图像
                hogel_img.save(output_path, quality=quality)
                
                # 获取图像尺寸
                hogel_width, hogel_height = hogel_img.size
                
                print(f"  已保存: {output_filename} ({hogel_width}x{hogel_height}) - 位置 ({row},{col})")
        
        print(f"\n处理完成!")
        print(f"  共生成 {total_hogels} 个hogel图像")
        print(f"  每个hogel尺寸: {tile_width * grid_size}x{tile_height * grid_size} 像素")
        print(f"  网格布局: {grid_size}×{grid_size} 个小方块")
        print(f"  输出文件夹: {output_folder}")
        
        return total_hogels

# 工厂函数
def create_processor(processor_type='horizontal'):
    """创建处理器实例"""
    if processor_type == 'horizontal':
        return HorizontalParallaxProcessor()
    elif processor_type == 'full':
        return FullParallaxProcessor()
    else:
        raise ValueError(f"不支持的处理器类型: {processor_type}")

# 兼容性函数
def process_hogel_images(input_folder, output_folder, C, hogel_width_fixed=500, 
                         hogel_height_fixed=None, quality=95):
    """兼容旧版本的函数"""
    processor = HorizontalParallaxProcessor()
    return processor.process(input_folder, output_folder, C, hogel_width_fixed, 
                            hogel_height_fixed, quality)

def process_full_parallax_images(input_folder, output_folder, canvas_width, 
                                 canvas_height, exposure_width, quality=95):
    """兼容旧版本的函数"""
    processor = FullParallaxProcessor()
    return processor.process(input_folder, output_folder, canvas_width, 
                            canvas_height, exposure_width, quality)