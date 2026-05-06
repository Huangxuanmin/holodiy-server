# Hogel图像处理系统 API 文档

## 概述

Hogel图像处理系统提供了一套完整的RESTful API，用于处理水平视差和全视差hogel图像。前端通过HTTP请求与后端交互，实现文件上传、图像处理、结果下载等功能。

## 基础信息

- **基础URL**: `http://localhost:8000`
- **内容类型**: `application/json` (除文件上传外)
- **文件上传**: `multipart/form-data`
- **跨域支持**: 已启用CORS

## API端点概览

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/api/health` | GET | 健康检查 | 无需 |
| `/api/upload` | POST | 上传图像文件 | 无需 |
| `/api/generate-hogel` | POST | 生成水平视差hogel | 无需 |
| `/api/generate-full-parallax-hogel` | POST | 生成全视差hogel | 无需 |
| `/api/download/<filename>` | GET | 下载单个文件 | 无需 |
| `/api/download-all` | GET | 下载所有文件(ZIP) | 无需 |
| `/api/clear-outputs` | POST | 清空输出目录 | 无需 |
| `/api/settings` | GET | 获取默认设置 | 无需 |
| `/api/estimate` | POST | 预估处理性能 | 无需 |

## 详细端点说明

### 1. 健康检查

检查API服务是否正常运行。

**端点**: `GET /api/health`

**请求参数**: 无

**响应示例**:
```json
{
  "status": "healthy",
  "message": "Hogel API 服务运行正常"
}
```

**状态码**:
- `200`: 服务正常
- `500`: 服务异常

### 2. 文件上传

上传图像文件到服务器。

**端点**: `POST /api/upload`

**请求格式**: `multipart/form-data`

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `files` | File[] | 是 | 图像文件数组 |

**支持的文件格式**:
- JPG/JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- BMP (`.bmp`)

**文件限制**:
- 单个文件最大: 10MB
- 总文件大小: 100MB

**响应示例** (成功):
```json
{
  "success": true,
  "message": "成功上传 3 个文件",
  "files": [
    {
      "filename": "image1.jpg",
      "size": 2048576,
      "preview_url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ...",
      "path": "uploads/image1.jpg"
    },
    {
      "filename": "image2.jpg",
      "size": 1572864,
      "preview_url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ...",
      "path": "uploads/image2.jpg"
    }
  ]
}
```

**响应示例** (失败):
```json
{
  "success": false,
  "error": "没有文件上传"
}
```

**状态码**:
- `200`: 上传成功
- `400`: 请求参数错误
- `413`: 文件过大
- `500`: 服务器内部错误

### 3. 生成水平视差hogel

使用水平视差算法处理上传的图像，生成hogel图像。

**端点**: `POST /api/generate-hogel`

**请求格式**: `multipart/form-data`

**请求参数**:
| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|--------|------|------|--------|------|
| `files` | File[] | 是 | - | 图像文件数组 |
| `C` | int | 否 | 10 | hogel数量，即每张图像分割的份数 |
| `width` | int | 否 | 500 | 每个hogel的固定像素宽度 | 
| `height` | int | 否 | null | 每个hogel的固定像素高度(可选) |
| `quality` | int | 否 | 95 | 输出图像质量(1-100) |

**算法说明**:
1. 将每张图像的宽度平均分成C份
2. 将每份通过OpenCV resize变换成固定尺寸
3. 提取所有图像的第i个位置(i从0到C-1)
4. 将所有图像的第i个位置按顺序水平排列组成一张hogel图像
5. 每张hogel图像的总宽度为: 图像数量 × (width/图像数量) = width

**响应示例** (成功):
```json
{
  "success": true,
  "message": "成功生成 10 个水平视差hogel图像",
  "hogels": [
    {
      "name": "hogel_horizontal_001.jpg",
      "size": "245.6 KB",
      "preview_url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ...",
      "download_url": "/api/download/hogel_horizontal_001.jpg"
    },
    {
      "name": "hogel_horizontal_002.jpg",
      "size": "238.9 KB",
      "preview_url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ...",
      "download_url": "/api/download/hogel_horizontal_002.jpg"
    }
  ],
  "log": "水平视差处理成功完成"
}
```

**状态码**:
- `200`: 处理成功
- `400`: 参数错误或没有文件
- `500`: 处理失败

### 4. 生成全视差hogel

使用全视差算法处理上传的图像，生成hogel图像。

**端点**: `POST /api/generate-full-parallax-hogel`

**请求格式**: `multipart/form-data`

**请求参数**:
| 参数名 | 类型 | 必填 | 默认值 | 描述 |
|--------|------|------|--------|------|
| `files` | File[] | 是 | - | 图像文件数组 |
| `canvas_width` | float | 否 | 100.0 | 画幅宽度(mm) |
| `canvas_height` | float | 否 | 100.0 | 画幅高度(mm) |
| `exposure_width` | float | 否 | 10.0 | 曝光宽度(mm) |
| `quality` | int | 否 | 95 | 输出图像质量(1-100) |

**算法说明**:
1. 计算C = 画幅宽度 / 曝光宽度
2. 将每张图像分割成C×C个小方块
3. 将所有图像同一位置的小方块按1:1网格拼接成hogel
4. 如果小方块数量不能1:1拼接，使用最接近的1:1数量

**响应示例** (成功):
```json
{
  "success": true,
  "message": "成功生成 25 个全视差hogel图像",
  "hogels": [
    {
      "name": "hogel_full_001.jpg",
      "size": "312.4 KB",
      "preview_url": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQ...",
      "download_url": "/api/download/hogel_full_001.jpg"
    }
  ],
  "log": "全视差处理成功完成"
}
```

**状态码**:
- `200`: 处理成功
- `400`: 参数错误或没有文件
- `500`: 处理失败

### 5. 下载单个文件

下载指定的hogel图像文件。

**端点**: `GET /api/download/<filename>`

**路径参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `filename` | string | 是 | 文件名 |

**响应**: 文件二进制流

**状态码**:
- `200`: 下载成功
- `404`: 文件不存在
- `500`: 服务器错误

### 6. 下载所有文件

将所有hogel图像文件打包为ZIP下载。

**端点**: `GET /api/download-all`

**响应**: ZIP文件二进制流

**响应头**:
- `Content-Type`: `application/zip`
- `Content-Disposition`: `attachment; filename="hogel_images.zip"`

**状态码**:
- `200`: 下载成功
- `500`: 打包失败

### 7. 清空输出目录

清空输出目录中的所有文件。

**端点**: `POST /api/clear-outputs`

**请求参数**: 无

**响应示例**:
```json
{
  "success": true,
  "message": "输出目录已清空"
}
```

**状态码**:
- `200`: 清空成功
- `500`: 清空失败

### 8. 获取默认设置

获取系统的默认处理参数设置。

**端点**: `GET /api/settings`

**请求参数**: 无

**响应示例**:
```json
{
  "success": true,
  "settings": {
    "horizontal": {
      "hogelCount": 10,
      "hogelWidth": 500,
      "heightMode": "fixed",
      "hogelHeight": 500,
      "quality": 95,
      "enableAntiAliasing": true,
      "enableOptimization": true
    },
    "full": {
      "canvasWidth": 100.0,
      "canvasHeight": 100.0,
      "exposureWidth": 10.0,
      "quality": 95
    }
  }
}
```

### 9. 预估处理性能

根据文件数量和大小预估处理所需资源。

**端点**: `POST /api/estimate`

**请求格式**: `application/json`

**请求参数**:
| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `fileCount` | int | 是 | 文件数量 |
| `totalSize` | int | 是 | 总文件大小(字节) |

**响应示例**:
```json
{
  "success": true,
  "estimate": {
    "processingTime": "~15s",
    "memoryUsage": "~120MB",
    "outputSize": "~80MB"
  }
}
```

## 前端交互流程

### 典型使用流程

1. **健康检查**
   ```javascript
   fetch('/api/health')
     .then(response => response.json())
     .then(data => console.log(data.status));
   ```

2. **文件上传**
   ```javascript
   const formData = new FormData();
   files.forEach(file => {
     formData.append('files', file);
   });
   
   fetch('/api/upload', {
     method: 'POST',
     body: formData
   });
   ```

3. **生成hogel** (水平视差示例)
   ```javascript
   const formData = new FormData();
   files.forEach(file => {
     formData.append('files', file);
   });
   formData.append('C', 10);
   formData.append('width', 500);
   formData.append('height', 500);
   formData.append('quality', 95);
   
   fetch('/api/generate-hogel', {
     method: 'POST',
     body: formData
   });
   ```

4. **下载结果**
   ```javascript
   // 下载单个文件
   window.open('/api/download/hogel_001.jpg');
   
   // 下载所有文件
   fetch('/api/download-all')
     .then(response => response.blob())
     .then(blob => {
       const url = window.URL.createObjectURL(blob);
       const a = document.createElement('a');
       a.href = url;
       a.download = 'hogel_images.zip';
       a.click();
     });
   ```

## 错误处理

### 错误响应格式
```json
{
  "success": false,
  "error": "错误描述信息"
}
```

### 常见错误码
- `400`: 请求参数错误
- `404`: 资源不存在
- `413`: 文件过大
- `415`: 不支持的媒体类型
- `500`: 服务器内部错误

## 数据模型

### 文件信息对象
```typescript
interface FileInfo {
  filename: string;      // 文件名
  size: number;         // 文件大小(字节)
  preview_url: string;  // 预览图base64 URL
  path: string;         // 文件路径
}
```

### Hogel结果对象
```typescript
interface HogelResult {
  name: string;         // 文件名
  size: string;         // 文件大小(格式化)
  preview_url: string;  // 预览图base64 URL
  download_url: string; // 下载URL
}
```

### 设置对象
```typescript
interface Settings {
  horizontal: {
    hogelCount: number;
    hogelWidth: number;
    heightMode: 'fixed' | 'original';
    hogelHeight?: number;
    quality: number;
    enableAntiAliasing: boolean;
    enableOptimization: boolean;
  };
  full: {
    canvasWidth: number;
    canvasHeight: number;
    exposureWidth: number;
    quality: number;
  };
}
```

## 注意事项

### 文件处理
1. 所有上传的文件会保存在`uploads/`目录
2. 处理结果保存在`outputs/`目录
3. 临时文件会在处理完成后自动清理
4. 建议定期清空输出目录以释放磁盘空间

### 性能考虑
1. 大图像处理需要较多内存
2. 多文件处理可能需要较长时间
3. 建议先使用预估功能了解资源需求
4. 处理过程中请勿关闭浏览器或中断连接

### 安全限制
1. 文件类型限制为图像格式
2. 文件大小限制为10MB/文件
3. 总请求大小限制为100MB
4. 文件名会进行安全过滤

## 开发说明

### 环境要求
- Python 3.9+
- Node.js 16+
- 现代浏览器(Chrome 90+, Firefox 88+, Safari 14+)

### 本地开发
1. 启动后端: `python flask_hogel_api.py`
2. 启动前端: `npm start`
3. 访问: `http://localhost:3000`

### 生产部署
1. 构建前端: `npm run build`
2. 使用生产级WSGI服务器(如Gunicorn)
3. 配置反向代理(如Nginx)
4. 设置环境变量和安全性配置

## 更新日志

### v1.0.0 (初始版本)
- 实现水平视差hogel处理
- 实现全视差hogel处理
- 提供完整的文件上传、处理、下载功能
- 基于Ant Design的React前端界面
- Flask后端RESTful API

---

**文档版本**: 1.0.0  
**最后更新**: 2026-04-11  
**维护者**: Hogel图像处理系统开发团队