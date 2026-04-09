# Hogel图处理工具（水平排列版本）

这个工具用于处理hogel图像，根据用户输入的hogel图个数参数C，读取文件夹中的每一张视图，并将图像宽度平均分成C份，每张图对应的位置按顺序水平排列组成一张hogel图。

## 功能说明

1. 读取指定文件夹中的所有JPG图像
2. 将每张图像的宽度平均分成C份
3. 将所有图像的第0个位置组成一张hogel图，第1个位置组成另一张hogel图，以此类推
4. 保存生成的hogel图到输出文件夹

## 文件结构

- `hogel_processor.py` - 主处理脚本（水平排列版本）
- `test_hogel.py` - 测试脚本
- `verify_horizontal_hogels.py` - 水平排列验证脚本
- `verify_hogels.py` - 垂直排列验证脚本（旧版本）
- `check_images.py` - 图像检查脚本
- `scarlett/` - 输入图像文件夹（50张1920x1080图像）
- `hogel_horizontal/` - 水平排列输出hogel图像文件夹
- `hogel_output/` - 垂直排列输出hogel图像文件夹（旧版本）

## 使用方法

### 方法1：使用主脚本直接运行

```bash
# 基本用法：分割成5个hogel图
python hogel_processor.py 5

# 使用自定义输入输出文件夹
python hogel_processor.py 10 --input "d:\AI_code\Hologram\scarlett" --output "d:\AI_code\Hologram\my_hogels"

# 查看帮助
python hogel_processor.py -h
```

### 方法2：使用测试脚本

```bash
# 分割成5个hogel图
python test_hogel.py 5

# 分割成10个hogel图
python test_hogel.py 10

# 使用自定义输入输出文件夹
python test_hogel.py 8 --input "d:\AI_code\Hologram\scarlett" --output "d:\AI_code\Hologram\my_hogels"
```

### 方法3：验证输出结果

```bash
# 验证生成的hogel图像
python verify_hogels.py
```

## 参数说明

- `C` (必需): hogel图个数，即每张图像要分割的份数
- `--input`: 输入图像文件夹路径（默认: `d:\AI_code\Hologram\scarlett`）
- `--output`: 输出hogel图像文件夹路径（默认: `d:\AI_code\Hologram\hogel_horizontal`）

## 示例

### 示例1：分割成5个hogel图（水平排列）

原始图像: 1920x1080像素 × 50张
每个hogel宽度: 1920 ÷ 5 = 384像素
每个hogel图像尺寸: 19200x1080像素 (50张图像水平拼接，384×50=19200)

### 示例2：分割成10个hogel图（水平排列）

原始图像: 1920x1080像素 × 50张
每个hogel宽度: 1920 ÷ 10 = 192像素
每个hogel图像尺寸: 9600x1080像素 (50张图像水平拼接，192×50=9600)

## 算法原理（水平排列）

1. **图像分割**: 将每张原始图像在宽度方向上平均分成C份
2. **hogel构建**: 将所有原始图像的第i个位置（i从0到C-1）提取出来
3. **水平拼接**: 将提取出的所有第i个位置按原始图像顺序水平排列成一张完整的hogel图像
4. **保存输出**: 保存C张hogel图像，命名为`hogel_000.jpg`到`hogel_(C-1).jpg`

## 技术要求

- Python 3.6+
- Pillow库 (图像处理)
- 可通过以下命令安装依赖:
  ```bash
  pip install pillow
  ```

## 验证方法

生成的hogel图像可以通过以下方式验证：
1. 检查图像尺寸是否符合预期
2. 检查图像数量是否正确（应为C张）
3. 检查每张hogel图像是否包含所有原始图像的对应位置
4. 使用`verify_horizontal_hogels.py`脚本进行自动验证（水平排列版本）
5. 使用`verify_hogels.py`脚本进行自动验证（垂直排列版本，旧版本）

## 注意事项

1. 所有输入图像应具有相同的尺寸
2. 图像宽度应能被C整除，否则会使用整数除法
3. 输出图像质量设置为95（高质量）
4. 输出文件夹会自动创建