# 通知系统 v2.0

## 快速开始

### 开发环境

```bash
# 启动后端
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 启动前端 (React)
cd frontend
npm install
npm run dev
```

### Docker 部署

```bash
# 开发环境
docker-compose -f docker-compose.dev.yml up

# 生产环境
docker-compose -f docker-compose.prod.yml up --build

# 完整环境 (含监控)
docker-compose --profile monitoring up
```

## 定时通知功能

支持创建在未来某个时间点自动发送的通知。

### 创建定时通知

在创建通知时添加 `scheduled_at` 字段：

```bash
curl -X POST http://localhost:8000/api/notifications \
  -H "Content-Type: application/json" \
  -d '{
    "title": "定时提醒",
    "message": "这是一条定时通知",
    "type": "info",
    "scheduled_at": "2026-06-03T10:00:00"
  }'
```

### 定时通知 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/notifications/scheduled` | GET | 获取所有定时通知，支持 `status` 参数筛选 |
| `/api/notifications/scheduled/pending` | GET | 获取已到期但未发送的定时通知 |
| `/api/notifications/{id}/cancel` | POST | 取消待发送的定时通知 |

### 定时通知状态

- `pending` — 待发送
- `sent` — 已发送
- `cancelled` — 已取消

### 调度器

后台调度器每 30 秒检查一次到期的定时通知，自动发送并更新状态。

---

## 统一错误码

| 错误码 | 说明 | HTTP 状态 |
|--------|------|-----------|
| SUCCESS | 成功 | 200 |
| ERR_VALIDATION | 参数校验失败 | 400 |
| ERR_NOT_FOUND | 资源不存在 | 404 |
| ERR_DUPLICATE | 资源重复 | 409 |
| ERR_PERMISSION | 权限不足 | 403 |
| ERR_INTERNAL | 内部错误 | 500 |

### 模块错误码

- **1000-1999**: 通用错误
- **2000-2999**: 认证模块
- **3000-3999**: 通知模块
- **4000-4999**: 模板模块
- **5000-5999**: 订阅模块
- **6000-6999**: API Key 模块
- **7000-7999**: 推送模块
- **8000-8999**: 调度模块

## 统一响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

## 日志格式

生产环境输出 JSON 格式:

```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "level": "INFO",
  "logger": "notification",
  "message": "通知创建成功",
  "request_id": "xxx"
}
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| APP_ENV | 环境 (production/development) | development |
| SECRET_KEY | JWT 密钥 | 自动生成 |
| PYTHONUNBUFFERED | 输出缓冲 | 1 |