# Hogel前端开发指南

## 项目概述

Hogel图像处理系统前端是一个基于React和Ant Design的单页应用，通过RESTful API与后端交互，提供图像上传、处理参数配置、结果展示和下载等功能。

## 技术栈

- **框架**: React 18.2.0
- **构建工具**: Vite 5.1.4
- **UI组件库**: Ant Design 5.16.0
- **图标**: @ant-design/icons 5.3.0
- **HTTP客户端**: Axios 1.6.0 (备用)
- **样式**: CSS + Ant Design样式系统

## 项目结构

```
holodiy-server/
├── index.html              # HTML入口文件
├── index.jsx              # React入口文件
├── App.jsx                # 主应用组件
├── App.css                # 全局样式
├── index.css              # 基础样式
├── vite.config.js         # Vite配置
├── package.json           # 依赖配置
└── components/            # React组件目录
    ├── FileUpload.jsx     # 文件上传组件
    ├── ProcessingSettings.jsx # 处理设置组件
    └── ResultsDisplay.jsx # 结果展示组件
```

## 组件说明

### 1. App.jsx (主应用组件)
**功能**: 应用布局、路由管理、状态管理、API调用协调

**主要状态**:
- `uploadedFiles`: 已上传的文件列表
- `processingSettings`: 处理参数设置
- `processingResults`: 处理结果列表
- `isProcessing`: 处理状态标志
- `apiStatus`: API健康状态

**核心方法**:
- `handleFileUpload()`: 处理文件上传
- `handleProcess()`: 调用处理API
- `handleDownloadAll()`: 批量下载结果

### 2. FileUpload.jsx (文件上传组件)
**功能**: 文件选择、拖拽上传、文件预览、上传进度显示

**Ant Design组件**:
- `Upload.Dragger`: 拖拽上传区域
- `List`: 文件列表显示
- `Image`: 图片预览
- `Progress`: 上传进度条
- `Button`: 操作按钮

**特性**:
- 支持多文件选择
- 拖拽上传支持
- 实时文件预览
- 文件大小和类型验证

### 3. ProcessingSettings.jsx (处理设置组件)
**功能**: 处理参数配置、处理模式选择、参数验证

**Ant Design组件**:
- `Tabs`: 水平/全视差模式切换
- `Form`: 参数表单
- `InputNumber`: 数字输入
- `Slider`: 滑块输入
- `Select`: 下拉选择
- `Switch`: 开关选项
- `Button`: 处理按钮

**配置分组**:
- **水平视差**: hogel数量、宽度、高度、质量等
- **全视差**: 画幅尺寸、曝光宽度、质量等

### 4. ResultsDisplay.jsx (结果展示组件)
**功能**: 结果展示、图片预览、文件下载、批量操作

**Ant Design组件**:
- `Card`: 结果卡片
- `Image`: 图片预览和放大
- `Statistic`: 统计信息显示
- `Progress`: 处理进度显示
- `Button`: 下载按钮

**特性**:
- 网格布局展示
- 图片hover效果
- 单个/批量下载
- 处理统计信息

## API集成

### 基础配置
Vite已配置代理，所有`/api/*`请求自动转发到`http://localhost:8000`

```javascript
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

### API服务层示例
```javascript
// apiService.js (建议创建)
class ApiService {
  constructor(baseURL = '/api') {
    this.baseURL = baseURL;
  }

  // 健康检查
  async checkHealth() {
    const response = await fetch(`${this.baseURL}/health`);
    return await response.json();
  }

  // 文件上传
  async uploadFiles(files) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    const response = await fetch(`${this.baseURL}/upload`, {
      method: 'POST',
      body: formData
    });
    
    return await response.json();
  }

  // 水平视差处理
  async processHorizontalParallax(files, params) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        formData.append(key, value);
      }
    });
    
    const response = await fetch(`${this.baseURL}/generate-hogel`, {
      method: 'POST',
      body: formData
    });
    
    return await response.json();
  }

  // 全视差处理
  async processFullParallax(files, params) {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        formData.append(key, value);
      }
    });
    
    const response = await fetch(`${this.baseURL}/generate-full-parallax-hogel`, {
      method: 'POST',
      body: formData
    });
    
    return await response.json();
  }

  // 下载文件
  async downloadFile(filename) {
    const response = await fetch(`${this.baseURL}/download/${filename}`);
    return await response.blob();
  }

  // 批量下载
  async downloadAll() {
    const response = await fetch(`${this.baseURL}/download-all`);
    return await response.blob();
  }

  // 获取设置
  async getSettings() {
    const response = await fetch(`${this.baseURL}/settings`);
    return await response.json();
  }

  // 预估处理
  async estimateProcessing(fileCount, totalSize) {
    const response = await fetch(`${this.baseURL}/estimate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fileCount, totalSize })
    });
    
    return await response.json();
  }

  // 清空输出
  async clearOutputs() {
    const response = await fetch(`${this.baseURL}/clear-outputs`, {
      method: 'POST'
    });
    
    return await response.json();
  }
}

export default new ApiService();
```

## 状态管理

### 推荐状态结构
```javascript
const [state, setState] = useState({
  // 文件状态
  uploadedFiles: [],
  selectedFiles: [],
  
  // 处理状态
  processingSettings: {
    horizontal: {
      hogelCount: 10,
      hogelWidth: 500,
      heightMode: 'fixed',
      hogelHeight: 500,
      quality: 95,
      enableAntiAliasing: true,
      enableOptimization: true
    },
    full: {
      canvasWidth: 100.0,
      canvasHeight: 100.0,
      exposureWidth: 10.0,
      quality: 95
    }
  },
  
  // 结果状态
  processingResults: [],
  currentResult: null,
  
  // UI状态
  isProcessing: false,
  apiStatus: 'checking',
  activeTab: 'upload',
  errors: []
});
```

### 状态更新工具
```javascript
// 状态更新辅助函数
const updateState = (updates) => {
  setState(prev => ({ ...prev, ...updates }));
};

// 文件管理
const addFiles = (newFiles) => {
  updateState({
    uploadedFiles: [...state.uploadedFiles, ...newFiles]
  });
};

const removeFile = (index) => {
  const newFiles = [...state.uploadedFiles];
  newFiles.splice(index, 1);
  updateState({ uploadedFiles: newFiles });
};

// 设置更新
const updateSettings = (settings) => {
  updateState({
    processingSettings: {
      ...state.processingSettings,
      ...settings
    }
  });
};
```

## 错误处理

### 错误边界组件
```javascript
import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('组件错误:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20, textAlign: 'center' }}>
          <h2>出错了</h2>
          <p>{this.state.error?.message || '未知错误'}</p>
          <button onClick={() => window.location.reload()}>
            重新加载
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
```

### API错误处理
```javascript
const handleApiError = (error, context) => {
  console.error(`API错误 [${context}]:`, error);
  
  // 显示用户友好的错误信息
  let userMessage = '操作失败，请重试';
  
  if (error.message.includes('Network')) {
    userMessage = '网络连接失败，请检查网络';
  } else if (error.message.includes('400')) {
    userMessage = '请求参数错误';
  } else if (error.message.includes('413')) {
    userMessage = '文件过大，请减小文件大小';
  } else if (error.message.includes('500')) {
    userMessage = '服务器内部错误，请稍后重试';
  }
  
  // 使用Ant Design的message组件
  message.error(userMessage);
  
  // 返回错误信息供组件使用
  return { success: false, error: userMessage };
};

// 使用示例
try {
  const result = await apiService.uploadFiles(files);
  if (!result.success) {
    throw new Error(result.error);
  }
  return result;
} catch (error) {
  return handleApiError(error, '文件上传');
}
```

## 性能优化

### 图片优化
```javascript
// 图片懒加载
import { LazyLoadImage } from 'react-lazy-load-image-component';
import 'react-lazy-load-image-component/src/effects/blur.css';

const OptimizedImage = ({ src, alt, ...props }) => (
  <LazyLoadImage
    effect="blur"
    src={src}
    alt={alt}
    {...props}
  />
);

// 图片压缩预览
const compressImage = (file, maxWidth = 800, quality = 0.8) => {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    
    reader.onload = (event) => {
      const img = new Image();
      img.src = event.target.result;
      
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // 计算缩放比例
        const scale = Math.min(maxWidth / img.width, 1);
        canvas.width = img.width * scale;
        canvas.height = img.height * scale;
        
        // 绘制缩放后的图片
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        
        // 转换为Blob
        canvas.toBlob(
          (blob) => resolve(blob),
          'image/jpeg',
          quality
        );
      };
    };
  });
};
```

### 组件优化
```javascript
// 使用React.memo避免不必要的重渲染
const MemoizedComponent = React.memo(({ data }) => {
  // 组件逻辑
}, (prevProps, nextProps) => {
  // 自定义比较函数
  return prevProps.data.id === nextProps.data.id;
});

// 使用useCallback缓存函数
const handleProcess = useCallback(async (processorType) => {
  // 处理逻辑
}, [uploadedFiles, processingSettings]);

// 使用useMemo缓存计算结果
const totalFileSize = useMemo(() => {
  return uploadedFiles.reduce((sum, file) => sum + file.size, 0);
}, [uploadedFiles]);
```

## 样式指南

### Ant Design主题定制
```javascript
// 自定义主题 (可在vite.config.js中配置)
import { theme } from 'antd';

const customTheme = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
    colorBgContainer: '#ffffff',
  },
  components: {
    Button: {
      borderRadius: 4,
    },
    Card: {
      borderRadius: 8,
    },
  },
};

// 在App中使用
import { ConfigProvider } from 'antd';

function App() {
  return (
    <ConfigProvider theme={customTheme}>
      {/* 应用内容 */}
    </ConfigProvider>
  );
}
```

### 响应式设计
```css
/* 移动端适配 */
@media (max-width: 768px) {
  .upload-area {
    padding: 20px;
  }
  
  .results-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .ant-layout-sider {
    display: none;
  }
}

@media (max-width: 480px) {
  .results-grid {
    grid-template-columns: 1fr;
  }
  
  .file-item {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .file-preview {
    margin-right: 0;
    margin-bottom: 8px;
  }
}
```

## 测试指南

### 组件测试示例
```javascript
// FileUpload.test.jsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import FileUpload from './FileUpload';

describe('FileUpload组件', () => {
  test('渲染上传区域', () => {
    render(<FileUpload onUpload={jest.fn()} uploadedFiles={[]} />);
    expect(screen.getByText('点击或拖拽文件到此区域上传')).toBeInTheDocument();
  });

  test('显示已上传文件', () => {
    const mockFiles = [
      new File(['content'], 'test.jpg', { type: 'image/jpeg' })
    ];
    
    render(<FileUpload onUpload={jest.fn()} uploadedFiles={mockFiles} />);
    expect(screen.getByText('test.jpg')).toBeInTheDocument();
  });
});
```

### API模拟测试
```javascript
// apiService.test.js
import ApiService from './apiService';

// 模拟fetch
global.fetch = jest.fn();

describe('ApiService', () => {
  beforeEach(() => {
    fetch.mockClear();
  });

  test('健康检查成功', async () => {
    const mockResponse = {
      status: 'healthy',
      message: '服务正常'
    };
    
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    });
    
    const result = await ApiService.checkHealth();
    expect(result).toEqual(mockResponse);
    expect(fetch).toHaveBeenCalledWith('/api/health');
  });

  test('文件上传失败处理', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ success: false, error: '上传失败' })
    });
    
    const files = [new File(['content'], 'test.jpg')];
    const result = await ApiService.uploadFiles(files);
    
    expect(result.success).toBe(false);
    expect(result.error).toBe('上传失败');
  });
});
```

## 部署指南

### 构建生产版本
```bash
# 安装依赖
npm install --legacy-peer-deps

# 构建
npm run build

# 预览构建结果
npm run preview
```

### 环境变量配置
```javascript
// .env.development
VITE_API_BASE_URL=http://localhost:8000

// .env.production
VITE_API_BASE_URL=/api

// 代码中使用
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api';
```

### Nginx配置示例
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 前端静态文件
    location / {
        root /path/to/build;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
    
    # API代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 开发工作流

### 1. 本地开发
```bash
# 启动后端
python flask_hogel_api.py

# 启动前端开发服务器
npm start

# 访问 http://localhost:3000
```

### 2. 代码规范
- 使用ESLint进行代码检查
- 使用Prettier进行代码格式化
- 遵循React Hooks规则
- 组件使用PascalCase命名
- 函数使用camelCase命名

### 3. 提交规范
```
feat: 新增功能
fix: 修复bug
docs: 文档更新
style: 代码格式
refactor: 代码重构
test: 测试相关
chore: 构建过程或辅助工具
```

## 常见问题

### Q: 文件上传进度不显示
A: 检查FormData是否正确构建，确保文件被正确添加到formData中。

### Q: 图片预览不显示
A: 检查图片URL格式，确保是有效的base64或URL。

### Q: API请求被CORS阻止
A: 确保后端CORS已正确配置，或使用Vite代理。

### Q: 处理大文件时内存不足
A: 优化图片压缩，分批次处理文件，增加内存限制提示。

### Q: 移动端样式异常
A: 检查响应式CSS，确保使用相对单位和媒体查询。

## 扩展开发

### 添加新处理算法
1. 在后端添加新的API端点
2. 在前端添加对应的设置表单
3. 更新API服务层
4. 添加处理按钮和状态管理

### 国际化支持
```javascript
// 使用react-i18next
import i18n from 'i18next';
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation();
  return <div>{t('welcome')}</div>;
}
```

### 离线支持
```javascript
// 使用Service Worker
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}

// 本地存储
const saveToLocalStorage = (key, data) => {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (error) {
    console.error('本地存储失败:', error);
  }
};
```

---

**文档版本**: 1.0.0  
**最后更新**: 2026-04-11  
**更多资源**: 
- [Ant Design文档](https://ant.design/components/overview/)
- [React文档](https://react.dev/)
- [Vite文档](https://vite.dev/)