import os
import sys
import argparse
import math
from PIL import Image
import numpy as np
import cv2

def calculate_optimal_grid(total_tiles):
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

def process_full_parallax_images(input_folder, output_folder, canvas_width, canvas_height, exposure_width, quality=95):
    """
    处理全视差图像生成hogel
    
    参数:
    input_folder: 输入图像文件夹路径
    output_folder: 输出hogel图像文件夹路径
    canvas_width: 画幅宽度（mm）
    canvas_height: 画幅高度（mm）
    exposure_width: 曝光宽度（mm）
    quality: 输出图像质量（1-100，默认95）
    
    算法步骤:
    1. 计算C = 画幅宽度 / 曝光宽度
    2. 将每张图像分割成C×C个小方块
    3. 将所有图像同一位置的小方块按1:1网格拼接成hogel
    4. 如果小方块数量不能1:1拼接，使用最接近的1:1数量
    """
    
    # 获取所有jpg文件
    image_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.jpg')]
    image_files.sort()  # 按文件名排序
    
    if not image_files:
        print(f"在文件夹 {input_folder} 中没有找到jpg图像文件")
        return
    
    print(f"找到 {len(image_files)} 个图像文件")
    
    # 读取第一张图像获取尺寸
    first_image_path = os.path.join(input_folder, image_files[0])
    with Image.open(first_image_path) as img:
        img_width, img_height = img.size
        mode = img.mode
    
    print(f"图像尺寸: {img_width}x{img_height}, 模式: {mode}")
    
    # 计算C（每张图像分割的份数）
    C = canvas_width / exposure_width
    if C <= 0:
        print(f"错误: C必须大于0 (canvas_width={canvas_width}, exposure_width={exposure_width})")
        return
    
    # 确保C是整数
    C = int(C)
    if C <= 0:
        print(f"错误: C必须是正整数，当前C={C}")
        return
    
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
    grid_size, used_tiles = calculate_optimal_grid(total_tiles_per_position)
    print(f"  最优网格布局: {grid_size}×{grid_size} = {used_tiles} 个小方块")
    
    if used_tiles < total_tiles_per_position:
        print(f"  注意: 将使用前 {used_tiles} 个小方块，舍弃 {total_tiles_per_position - used_tiles} 个")
    
    # 创建输出文件夹
    os.makedirs(output_folder, exist_ok=True)
    
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

def main():
    parser = argparse.ArgumentParser(description='生成全视差hogel图像')
    parser.add_argument('--input', type=str, default=r'd:\AI_code\Hologram\scarlett',
                       help='输入图像文件夹路径 (默认: d:\\AI_code\\Hologram\\scarlett)')
    parser.add_argument('--output', type=str, default=r'd:\AI_code\Hologram\full_parallax_hogel',
                       help='输出hogel图像文件夹路径 (默认: d:\\AI_code\\Hologram\\full_parallax_hogel)')
    parser.add_argument('--canvas-width', type=float, required=True,
                       help='画幅宽度 (mm)')
    parser.add_argument('--canvas-height', type=float, required=True,
                       help='画幅高度 (mm)')
    parser.add_argument('--exposure-width', type=float, required=True,
                       help='曝光宽度 (mm)')
    parser.add_argument('--quality', type=int, default=95,
                       help='输出图像质量 (1-100，默认: 95)')
    
    args = parser.parse_args()
    
    # 参数验证
    if args.canvas_width <= 0:
        print("错误: 画幅宽度必须大于0")
        sys.exit(1)
    
    if args.canvas_height <= 0:
        print("错误: 画幅高度必须大于0")
        sys.exit(1)
    
    if args.exposure_width <= 0:
        print("错误: 曝光宽度必须大于0")
        sys.exit(1)
    
    if args.exposure_width > args.canvas_width:
        print("错误: 曝光宽度不能大于画幅宽度")
        sys.exit(1)
    
    if args.quality < 1 or args.quality > 100:
        print("错误: 图像质量必须在1-100之间")
        sys.exit(1)
    
    print("开始生成全视差hogel图像...")
    print(f"输入文件夹: {args.input}")
    print(f"输出文件夹: {args.output}")
    print(f"画幅尺寸: {args.canvas_width}mm × {args.canvas_height}mm")
    print(f"曝光宽度: {args.exposure_width}mm")
    print(f"输出质量: {args.quality}")
    
    # 调用处理函数
    process_full_parallax_images(
        input_folder=args.input,
        output_folder=args.output,
        canvas_width=args.canvas_width,
        canvas_height=args.canvas_height,
        exposure_width=args.exposure_width,
        quality=args.quality
    )

if __name__ == "__main__":
    main()