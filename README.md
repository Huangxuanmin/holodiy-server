# Hogel图像处理系统

一个基于Flask后端和React前端的全栈应用，用于处理水平视差和全视差hogel图像。

## 功能特性

### 后端功能
- 统一的hogel处理模块，封装了水平视差和全视差两种算法
- RESTful API接口，支持文件上传、处理、下载
- 图像预览生成和base64编码
- 临时文件管理和清理

### 前端功能
- 基于Ant Design的现代化UI界面
- 拖拽式文件上传，支持批量上传
- 两种处理模式：水平视差和全视差
- 实时参数配置和预览
- 处理结果展示和下载
- API健康状态监控

## 系统架构

```
hogel_processing.py      # 统一的hogel处理模块
flask_hogel_api.py       # Flask后端API
App.js                   # React主应用
components/              # React组件
  FileUpload.js          # 文件上传组件
  ProcessingSettings.js  # 处理设置组件
  ResultsDisplay.js      # 结果展示组件
```

## 安装和运行

### 方法一：使用启动脚本（推荐）
1. 双击运行 `start.bat`
2. 系统将自动安装依赖并启动服务

### 方法二：手动启动

#### 1. 安装Python依赖
```bash
pip install -r requirements.txt
```

#### 2. 启动Flask后端
```bash
python flask_hogel_api.py
```
后端将在 http://localhost:8000 启动

#### 3. 安装Node.js依赖
```bash
npm install
```

#### 4. 启动React前端
```bash
npm start
```
前端将在 http://localhost:3000 启动

## API接口

### 健康检查
```
GET /api/health
```

### 文件上传
```
POST /api/upload
Content-Type: multipart/form-data
```

### 生成水平视差hogel
```
POST /api/generate-hogel
参数:
- C: hogel数量 (默认: 10)
- width: hogel宽度像素 (默认: 500)
- height: hogel高度像素 (可选)
- quality: 输出质量 (默认: 95)
```

### 生成全视差hogel
```
POST /api/generate-full-parallax-hogel
参数:
- canvas_width: 画幅宽度mm (默认: 100.0)
- canvas_height: 画幅高度mm (默认: 100.0)
- exposure_width: 曝光宽度mm (默认: 10.0)
- quality: 输出质量 (默认: 95)
```

### 下载文件
```
GET /api/download/<filename>
```

### 下载全部文件
```
GET /api/download-all
```

### 获取默认设置
```
GET /api/settings
```

## 使用流程

1. **上传图像**
   - 点击"文件上传"菜单
   - 拖拽或选择图像文件（支持JPG、PNG、BMP格式）
   - 点击"开始上传"

2. **配置处理参数**
   - 点击"处理设置"菜单
   - 选择处理模式：水平视差或全视差
   - 配置相关参数
   - 点击"生成"按钮开始处理

3. **查看和下载结果**
   - 点击"处理结果"菜单查看生成的hogel图像
   - 点击图像可预览大图
   - 点击"下载"按钮下载单个文件
   - 点击"下载全部"按钮打包下载所有文件

## 技术栈

### 后端
- Python 3.9+
- Flask 3.0.0
- Pillow 10.1.0 (图像处理)
- OpenCV 4.8.1 (图像resize)
- NumPy 1.26.2

### 前端
- React 18.2.0
- Ant Design 5.16.0 (UI组件库)
- Axios 1.6.0 (HTTP客户端)

## 目录结构

```
uploads/          # 上传文件存储目录
outputs/          # 处理结果存储目录
components/       # React组件目录
  FileUpload.js   # 文件上传组件
  ProcessingSettings.js # 处理设置组件
  ResultsDisplay.js # 结果展示组件
hogel_processing.py # 统一的hogel处理模块
flask_hogel_api.py  # Flask后端API
App.js            # React主应用
index.js          # React入口文件
index.html        # HTML模板
package.json      # 前端依赖配置
requirements.txt  # 后端依赖配置
start.bat         # 启动脚本
```

## 注意事项

1. **文件大小限制**: 单个文件不超过10MB
2. **支持格式**: JPG、PNG、BMP图像格式
3. **处理时间**: 根据图像数量和大小，处理时间可能较长
4. **内存使用**: 大图像处理可能需要较多内存
5. **浏览器兼容**: 建议使用Chrome、Firefox等现代浏览器

## 故障排除

### 后端启动失败
- 检查Python版本（需要3.9+）
- 检查依赖是否安装：`pip list`
- 检查端口8000是否被占用

### 前端启动失败
- 检查Node.js版本（需要16+）
- 检查依赖是否安装：`npm list`
- 检查端口3000是否被占用

### 文件上传失败
- 检查文件格式是否支持
- 检查文件大小是否超过限制
- 检查网络连接

### 处理失败
- 检查图像尺寸是否一致
- 检查参数设置是否合理
- 查看控制台错误信息

## 开发说明

### 添加新的处理算法
1. 在 `hogel_processing.py` 中添加新的处理器类
2. 继承 `HogelProcessor` 基类
3. 实现 `process` 方法
4. 在 `create_processor` 函数中添加新的处理器类型
5. 在Flask API中添加对应的端点
6. 在前端添加对应的设置界面

### 修改UI界面
1. 修改 `App.css` 中的样式
2. 修改对应组件的JSX结构
3. 使用Ant Design组件库的文档参考

## 许可证

本项目仅供学习和研究使用。