# Hogel API 快速参考

## 基础信息
- **基础URL**: `http://localhost:8000`
- **前端代理**: `http://localhost:3000` (Vite开发服务器)
- **CORS**: 已启用

## 快速开始

### 1. 检查服务状态
```bash
curl http://localhost:8000/api/health
```

### 2. 上传文件
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg"
```

### 3. 生成水平视差hogel
```bash
curl -X POST http://localhost:8000/api/generate-hogel \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "C=10" \
  -F "width=500" \
  -F "height=500" \
  -F "quality=95"
```

### 4. 生成全视差hogel
```bash
curl -X POST http://localhost:8000/api/generate-full-parallax-hogel \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "canvas_width=100.0" \
  -F "canvas_height=100.0" \
  -F "exposure_width=10.0" \
  -F "quality=95"
```

## API端点速查表

### 健康检查
```
GET /api/health
```

### 文件管理
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/upload` | POST | 上传图像文件 |
| `/api/download/<filename>` | GET | 下载单个文件 |
| `/api/download-all` | GET | 下载所有文件(ZIP) |
| `/api/clear-outputs` | POST | 清空输出目录 |

### 图像处理
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/generate-hogel` | POST | 水平视差处理 |
| `/api/generate-full-parallax-hogel` | POST | 全视差处理 |

### 系统功能
| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/settings` | GET | 获取默认设置 |
| `/api/estimate` | POST | 预估处理性能 |

## 前端JavaScript示例

### 初始化检查
```javascript
// 检查API健康状态
async function checkHealth() {
  try {
    const response = await fetch('/api/health');
    const data = await response.json();
    return data.status === 'healthy';
  } catch (error) {
    console.error('API健康检查失败:', error);
    return false;
  }
}
```

### 文件上传
```javascript
async function uploadFiles(files) {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  
  const response = await fetch('/api/upload', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}
```

### 处理图像
```javascript
async function processHorizontalParallax(files, settings) {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  
  // 添加处理参数
  formData.append('C', settings.hogelCount || 10);
  formData.append('width', settings.hogelWidth || 500);
  if (settings.hogelHeight) {
    formData.append('height', settings.hogelHeight);
  }
  formData.append('quality', settings.quality || 95);
  
  const response = await fetch('/api/generate-hogel', {
    method: 'POST',
    body: formData
  });
  
  return await response.json();
}
```

### 下载结果
```javascript
// 下载单个文件
function downloadFile(filename) {
  window.open(`/api/download/${filename}`, '_blank');
}

// 下载所有文件
async function downloadAll() {
  try {
    const response = await fetch('/api/download-all');
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'hogel_images.zip';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } catch (error) {
    console.error('下载失败:', error);
  }
}
```

## 错误处理

### 通用错误格式
```json
{
  "success": false,
  "error": "错误描述"
}
```

### 常见错误
```javascript
// 处理API响应
async function handleApiResponse(response) {
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `HTTP ${response.status}`);
  }
  return await response.json();
}

// 使用示例
try {
  const data = await handleApiResponse(response);
  console.log('成功:', data);
} catch (error) {
  console.error('API错误:', error.message);
  // 显示错误提示给用户
}
```

## 数据类型

### 文件对象
```javascript
{
  filename: "image.jpg",      // 文件名
  size: 2048576,             // 文件大小(字节)
  preview_url: "data:image/jpeg;base64,...", // 预览图
  path: "uploads/image.jpg"  // 服务器路径
}
```

### Hogel结果对象
```javascript
{
  name: "hogel_001.jpg",     // 文件名
  size: "245.6 KB",          // 格式化大小
  preview_url: "data:image/jpeg;base64,...", // 预览图
  download_url: "/api/download/hogel_001.jpg" // 下载链接
}
```

## 配置参数

### 水平视差默认参数
```javascript
const horizontalDefaults = {
  hogelCount: 10,      // C值，分割份数
  hogelWidth: 500,     // 输出宽度(像素)
  hogelHeight: 500,    // 输出高度(像素)
  quality: 95,         // JPEG质量(1-100)
  heightMode: 'fixed'  // 高度模式: 'fixed'或'original'
};
```

### 全视差默认参数
```javascript
const fullParallaxDefaults = {
  canvasWidth: 100.0,   // 画幅宽度(mm)
  canvasHeight: 100.0,  // 画幅高度(mm)
  exposureWidth: 10.0,  // 曝光宽度(mm)
  quality: 95           // JPEG质量(1-100)
};
```

## 实用工具函数

### 获取默认设置
```javascript
async function getDefaultSettings() {
  const response = await fetch('/api/settings');
  const data = await response.json();
  return data.settings;
}
```

### 预估处理时间
```javascript
async function estimateProcessing(fileCount, totalSize) {
  const response = await fetch('/api/estimate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fileCount, totalSize })
  });
  const data = await response.json();
  return data.estimate;
}
```

### 清空输出目录
```javascript
async function clearOutputs() {
  const response = await fetch('/api/clear-outputs', {
    method: 'POST'
  });
  return await response.json();
}
```

## 开发提示

### 1. 前端代理配置
Vite开发服务器已配置代理，前端请求`/api/*`会自动转发到`http://localhost:8000`

### 2. 文件大小限制
- 单个文件: 10MB
- 总请求大小: 100MB

### 3. 支持的文件类型
- `.jpg`, `.jpeg`
- `.png`
- `.bmp`

### 4. 处理状态监控
```javascript
// 轮询处理状态
async function pollProcessingStatus(taskId, interval = 1000) {
  return new Promise((resolve, reject) => {
    const checkStatus = async () => {
      try {
        const response = await fetch(`/api/status/${taskId}`);
        const data = await response.json();
        
        if (data.status === 'completed') {
          resolve(data.result);
        } else if (data.status === 'failed') {
          reject(new Error(data.error));
        } else {
          setTimeout(checkStatus, interval);
        }
      } catch (error) {
        reject(error);
      }
    };
    
    checkStatus();
  });
}
```

## 故障排除

### 常见问题
1. **CORS错误**: 确保后端CORS已启用
2. **文件上传失败**: 检查文件大小和类型限制
3. **处理超时**: 大文件处理可能需要较长时间
4. **内存不足**: 减少同时处理的文件数量

### 调试建议
```javascript
// 启用详细日志
const DEBUG = true;

async function apiCall(endpoint, options = {}) {
  if (DEBUG) {
    console.log(`API调用: ${endpoint}`, options);
  }
  
  try {
    const response = await fetch(endpoint, options);
    
    if (DEBUG) {
      console.log(`响应状态: ${response.status}`);
    }
    
    const data = await response.json();
    
    if (DEBUG) {
      console.log('响应数据:', data);
    }
    
    return data;
  } catch (error) {
    if (DEBUG) {
      console.error('API调用失败:', error);
    }
    throw error;
  }
}
```

---

**文档版本**: 1.0.0  
**最后更新**: 2026-04-11  
**更多信息**: 参见完整API文档 `API_DOCUMENTATION.md`