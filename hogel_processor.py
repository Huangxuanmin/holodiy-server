import os
import sys
import argparse
from PIL import Image
import numpy as np
import cv2

def process_hogel_images(input_folder, output_folder, C, hogel_width_fixed=500, hogel_height_fixed=None, quality=95):
    """
    处理hogel图像（固定宽高版本，使用OpenCV resize）
    
    参数:
    input_folder: 输入图像文件夹路径
    output_folder: 输出hogel图像文件夹路径
    C: hogel图个数，即每张图像要分割的份数
    hogel_width_fixed: 每个hogel的固定像素宽度（默认500px）
    hogel_height_fixed: 每个hogel的固定像素高度（默认None，表示保持原始高度）
    quality: 输出图像质量（1-100，默认95）
    
    算法:
    1. 将每张图像的宽度平均分成C份
    2. 将每份通过OpenCV resize变换成:
       - 宽度: hogel_width_fixed/图像数量 像素
       - 高度: hogel_height_fixed 像素（如果提供）或保持原始高度
    3. 提取所有图像的第i个位置（i从0到C-1）
    4. 将所有图像的第i个位置按顺序水平排列组成一张hogel图像
    5. 每张hogel图像的总宽度为: 图像数量 × (hogel_width_fixed/图像数量) = hogel_width_fixed
    6. 保存C张hogel图像
    
    示例 (C=10, width=500px, height=500px, 50张图像):
    - 每份原始宽度: 1920÷10=192px, 高度: 1080px
    - Resize后每份: 宽度10px (500÷50), 高度500px
    - 拼接宽度: 50×10=500px
    - 最终hogel尺寸: 500×500px
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
        width, height = img.size
        mode = img.mode
    
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
    os.makedirs(output_folder, exist_ok=True)
    
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

def main():
    parser = argparse.ArgumentParser(description='处理hogel图像（固定宽度版本）')
    parser.add_argument('C', type=int, help='hogel图个数，即每张图像要分割的份数')
    parser.add_argument('--input', type=str, default=r'd:\AI_code\Hologram\scarlett',
                       help='输入图像文件夹路径 (默认: d:\\AI_code\\Hologram\\scarlett)')
    parser.add_argument('--output', type=str, default=r'd:\AI_code\Hologram\hogel_fixed_width',
                       help='输出hogel图像文件夹路径 (默认: d:\\AI_code\\Hologram\\hogel_fixed_width)')
    parser.add_argument('--width', type=int, default=500,
                       help='每个hogel的固定像素宽度 (默认: 500)')
    parser.add_argument('--height', type=int, default=None,
                       help='每个hogel的固定像素高度 (默认: None，保持原始高度)')
    parser.add_argument('--quality', type=int, default=95,
                       help='输出图像质量 (1-100，默认: 95)')
    
    args = parser.parse_args()
    
    if args.C <= 0:
        print("错误: C必须大于0")
        sys.exit(1)
    
    if args.width <= 0:
        print("错误: hogel宽度必须大于0")
        sys.exit(1)
    
    # 先获取图像文件列表以检查整除性
    try:
        image_files = [f for f in os.listdir(args.input) if f.lower().endswith('.jpg')]
        if image_files:
            if args.width % len(image_files) != 0:
                print(f"警告: hogel宽度 {args.width} 不能被图像数量 {len(image_files)} 整除，将使用整数除法")
        else:
            print(f"警告: 在文件夹 {args.input} 中没有找到jpg图像文件")
    except Exception as e:
        print(f"警告: 无法检查图像文件: {e}")
    
    print(f"开始处理hogel图像（固定宽高版本）...")
    print(f"输入文件夹: {args.input}")
    print(f"输出文件夹: {args.output}")
    print(f"hogel图个数(C): {args.C}")
    print(f"每个hogel的固定宽度: {args.width}px")
    if args.height is not None:
        print(f"每个hogel的固定高度: {args.height}px")
    else:
        print(f"每个hogel的高度: 保持原始高度")
    print(f"输出图像质量: {args.quality}")
    
    process_hogel_images(args.input, args.output, args.C, args.width, args.height, args.quality)

if __name__ == "__main__":
    main()