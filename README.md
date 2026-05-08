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

### 统一响应格式

除文件下载类接口（直接返回文件流）外，所有 JSON 接口均遵循：

```json
{
  "status": 0,
  "msg": "ok",
  "data": {}
}
```

- `status`：业务状态码，`0` 表示成功，非 `0` 表示失败。
- `msg`：提示文案，失败时由前端 toast 抛出。
- `data`：业务数据，失败时通常为 `null`。

新增接口时请使用 `app/responses.py` 提供的 `ok()` / `err()` 帮助函数构造响应。

### 接口列表

#### Hogel 图像处理（`app/routes.py`）

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

#### 账号与登录（`app/auth_routes.py`，前缀 `/api/auth`）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 邮箱/手机号 + 密码 注册 |
| POST | `/api/auth/login/password` | 邮箱/手机号 + 密码 登录 |
| POST | `/api/auth/send-sms-code` | 发送手机验证码 |
| POST | `/api/auth/login/sms` | 短信验证码登录（不存在则自动注册） |
| POST | `/api/auth/send-email-code` | 发送邮箱验证码 |
| POST | `/api/auth/login/email-code` | 邮箱验证码登录（不存在则自动注册） |
| POST | `/api/auth/register/email-code` | 邮箱验证码注册（可设置初始密码） |
| POST | `/api/auth/oauth/google` | Google 第三方登录 |
| POST | `/api/auth/oauth/wechat` | 微信第三方登录 |
| GET  | `/api/auth/wechat/authorize` | 获取微信扫码登录授权地址 |
| GET  | `/api/auth/wechat/callback` | 微信授权回调（重定向回前端并带 token） |
| GET  | `/api/auth/me` | 获取当前登录用户信息（需 token） |
| POST | `/api/auth/logout` | 退出登录（需 token） |

#### 图生 3D（`app/hitem3d_routes.py`，前缀 `/api/image-to-3d`）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/image-to-3d/submit` | 提交图生 3D 任务（需 token） |
| GET  | `/api/image-to-3d/query` | 查询任务状态（需 token） |
| DELETE | `/api/image-to-3d/tasks/<task_id>` | 删除指定任务（需 token） |
| GET  | `/api/image-to-3d/thumb/<name>` | 获取任务缩略图 |

#### 资产库（`app/assets_routes.py`，前缀 `/api/assets`）

统一的资产列表接口，覆盖 3D 模型 / 视差图 / Hogels 三类资产，均写入 `hitem3d_tasks` 表并通过 `asset_type` 字段区分。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/assets/list` | 列出当前用户资产（需 token），可选 `?type=model_3d\|parallax\|hogel` 过滤；不传则返回全部 |

返回字段：`task_id`、`asset_type`、`state`、`model_url`、`cover_url`、`thumb_url`、`created_at`、`updated_at` 等；其中 3D 模型的非终态任务会同步拉取 Hitem3D 上游状态，成功后自动触发 OSS 转存并返回签名链接。

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
