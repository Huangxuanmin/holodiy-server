# Holodiy Server

Hogel 图像处理后端 API 服务，基于 Flask 实现。提供水平视差和全视差两种 hogel 图像生成算法。

> 前端代码位于独立项目 [`../holodiy-fe`](../holodiy-fe)。

## 目录结构

```
holodiy-server/
├── run.py                  # 入口脚本
├── requirements.txt
├── app/                    # Flask 应用
│   ├── __init__.py         # create_app() 工厂
│   ├── config.py           # 配置常量
│   ├── routes.py           # API 路由（Blueprint）
│   └── utils.py            # 文件/预览/打包工具函数
├── processing/             # Hogel 处理算法
│   ├── __init__.py
│   ├── base.py             # HogelProcessor 基类
│   ├── horizontal.py       # 水平视差处理器
│   ├── full_parallax.py    # 全视差处理器
│   └── factory.py          # create_processor 工厂
├── tests/
│   └── test_api.py         # API 集成测试脚本
├── docs/
│   ├── API.md              # API 详细文档
│   └── API_QUICK_REFERENCE.md
├── uploads/                # 上传文件（运行时生成）
└── outputs/                # 处理结果（运行时生成）
```

## 安装与运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务（监听 http://0.0.0.0:8000）
python run.py
```

## API 概览

所有接口以 `/api` 为前缀：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/health` | 健康检查 |
| POST | `/api/upload` | 上传图像（绑定 taskId） |
| POST | `/api/generate-hogel` | 生成水平视差 hogel |
| POST | `/api/generate-full-parallax-hogel` | 生成全视差 hogel |
| GET  | `/api/download/<task_id>/<filename>` | 下载单个结果文件 |
| GET  | `/api/download/<filename>` | 下载文件（兼容旧路径） |
| GET  | `/api/download-all/<task_id>` | 下载指定任务的全部结果（zip） |
| GET  | `/api/download-all` | 下载所有输出（兼容旧路径） |
| POST | `/api/clear-outputs` | 清空输出目录 |
| GET  | `/api/settings` | 获取默认参数 |
| POST | `/api/estimate` | 预估处理性能 |

完整字段与示例参见 [`docs/API.md`](docs/API.md) 与 [`docs/API_QUICK_REFERENCE.md`](docs/API_QUICK_REFERENCE.md)。

## 技术栈

- Python 3.9+
- Flask 3.x + flask-cors
- Pillow / OpenCV / NumPy（图像处理）

## 测试

启动服务后，运行集成测试脚本：

```bash
python tests/test_api.py
```

## 开发说明

新增 hogel 处理算法的步骤：

1. 在 `processing/` 下新增文件（如 `my_algo.py`），创建继承自 `HogelProcessor` 的处理器类，并实现 `process` 方法。
2. 在 `processing/factory.py` 的 `create_processor` 中注册新的处理器类型。
3. 在 `processing/__init__.py` 中导出新类（可选）。
4. 在 `app/routes.py` 中添加对应的 API 端点。
