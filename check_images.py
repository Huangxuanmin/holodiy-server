import os
from PIL import Image

def check_images():
    folder_path = r"d:\AI_code\Hologram\scarlett"
    
    # 获取所有jpg文件
    image_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.jpg')]
    print(f"找到 {len(image_files)} 个图像文件")
    
    if not image_files:
        print("没有找到图像文件")
        return
    
    # 检查前几个文件的尺寸
    print("\n检查前5个图像的尺寸:")
    for i, filename in enumerate(sorted(image_files)[:5]):
        try:
            img_path = os.path.join(folder_path, filename)
            with Image.open(img_path) as img:
                width, height = img.size
                print(f"{filename}: {width}x{height}, 模式: {img.mode}")
        except Exception as e:
            print(f"无法读取 {filename}: {e}")

if __name__ == "__main__":
    check_images()