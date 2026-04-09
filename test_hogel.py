#!/usr/bin/env python
"""
hogel图处理测试脚本（水平排列版本）
使用示例:
1. 分割成5个hogel图: python test_hogel.py 5
2. 分割成10个hogel图: python test_hogel.py 10
3. 使用自定义输入输出文件夹: python test_hogel.py 8 --input "d:\AI_code\Hologram\scarlett" --output "d:\AI_code\Hologram\hogel_horizontal"
"""

import subprocess
import sys

def run_hogel_processor(C, input_folder=None, output_folder=None):
    """运行hogel处理器"""
    
    cmd = [sys.executable, "hogel_processor.py", str(C)]
    
    if input_folder:
        cmd.extend(["--input", input_folder])
    
    if output_folder:
        cmd.extend(["--output", output_folder])
    
    print(f"运行命令: {' '.join(cmd)}")
    print("-" * 50)
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("错误输出:")
        print(result.stderr)
    
    return result.returncode

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n请提供hogel图个数参数C")
        print("示例: python test_hogel.py 5")
        sys.exit(1)
    
    try:
        C = int(sys.argv[1])
    except ValueError:
        print(f"错误: '{sys.argv[1]}' 不是有效的整数")
        sys.exit(1)
    
    # 解析可选参数
    input_folder = None
    output_folder = None
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--input" and i + 1 < len(sys.argv):
            input_folder = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--output" and i + 1 < len(sys.argv):
            output_folder = sys.argv[i + 1]
            i += 2
        else:
            print(f"警告: 忽略未知参数 {sys.argv[i]}")
            i += 1
    
    print(f"测试hogel图处理，C={C}")
    if input_folder:
        print(f"输入文件夹: {input_folder}")
    if output_folder:
        print(f"输出文件夹: {output_folder}")
    
    return_code = run_hogel_processor(C, input_folder, output_folder)
    
    if return_code == 0:
        print("\n测试成功完成!")
    else:
        print(f"\n测试失败，返回码: {return_code}")
    
    sys.exit(return_code)

if __name__ == "__main__":
    main()