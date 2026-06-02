"""
通知系统后端 - 完整版
FastAPI + SQLite + WebSocket + JWT + 多渠道推送
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List
import asyncio
import json
import logging
import os
import uuid
import hashlib
import secrets

from storage import (
    init_db, NotificationStorage, TemplateStorage, UserStorage,
    APIKeyStorage, SubscriptionStorage
)
import scheduler


# ============== 数据模型 ==============

class NotificationType(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"


class NotificationCreate(BaseModel):
    title: str
    message: str
    type: NotificationType = NotificationType.INFO
    category: str = "general"
    tags: List[str] = []
    duration: float = 5.0
    scheduled_at: Optional[datetime] = None  # 定时发送时间，为空则立即发送


class TemplateCreate(BaseModel):
    name: str
    title: str
    message: str
    type: NotificationType = NotificationType.INFO
    category: str = "general"
    variables: List[str] = []


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class APIKeyCreate(BaseModel):
    name: str
    permissions: List[str] = ["read"]


class SubscriptionCreate(BaseModel):
    channel: str  # email, dingtalk, feishu
    config: dict
    types: List[str] = []
    categories: List[str] = []


# ============== JWT 认证 ==============

SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 小时

# 简单的 token 存储 (生产环境用 Redis)
tokens = {}


def create_token(user_id: str, username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "username": username,
        "exp": expire.timestamp()
    }
    # 简化版: 直接 base64 编码
    import base64
    token = base64.b64encode(json.dumps(payload).encode()).decode()
    tokens[token] = payload
    return token


def verify_token(token: str) -> Optional[dict]:
    try:
        import base64
        payload = json.loads(base64.b64decode(token.encode()).decode())
        if payload.get("exp", 0) < datetime.utcnow().timestamp():
            return None
        return payload
    except:
        return None


async def get_current_user(authorization: str = None):
    """从 Header 获取当前用户"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    payload = verify_token(token)
    return payload


# ============== 存储实例 ==============

notification_storage = NotificationStorage()
template_storage = TemplateStorage()
user_storage = UserStorage()
apikey_storage = APIKeyStorage()
subscription_storage = SubscriptionStorage()


# ============== WebSocket 管理 ==============

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                disconnected.append(conn)
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


# ============== 推送渠道 ==============

async def push_to_channels(notification: dict):
    """推送到所有订阅渠道"""
    subscriptions = await subscription_storage.get_all()

    for sub in subscriptions:
        # 检查是否匹配类型和分类
        if sub.get("types") and notification.get("type") not in sub["types"]:
            continue
        if sub.get("categories") and notification.get("category") not in sub["categories"]:
            continue

        channel = sub["channel"]
        config = sub.get("config", {})

        try:
            if channel == "desktop":
                await push_desktop(notification, config)
            elif channel == "email":
                await push_email(notification, config)
            elif channel == "dingtalk":
                await push_dingtalk(notification, config)
            elif channel == "feishu":
                await push_feishu(notification, config)
        except Exception as e:
            print(f"推送失败 [{channel}]: {e}")


async def push_desktop(notification: dict, config: dict):
    """桌面通知 (macOS)"""
    import subprocess

    title = notification["title"]
    message = notification["message"]

    script = f'display notification "{message}" with title "{title}"'
    subprocess.run(["osascript", "-e", script], capture_output=True)


async def push_email(notification: dict, config: dict):
    """邮件推送"""
    import smtplib
    from email.mime.text import MIMEText

    smtp_host = config.get("smtp_host", "smtp.gmail.com")
    smtp_port = config.get("smtp_port", 587)
    smtp_user = config.get("smtp_user")
    smtp_password = config.get("smtp_password")
    to_email = config.get("to_email")

    if not all([smtp_user, smtp_password, to_email]):
        return

    msg = MIMEText(f"{notification['message']}\n\n类型: {notification['type']}")
    msg["Subject"] = f"[{notification['type'].upper()}] {notification['title']}"
    msg["From"] = smtp_user
    msg["To"] = to_email

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)


async def push_dingtalk(notification: dict, config: dict):
    """钉钉 Webhook"""
    import httpx

    webhook_url = config.get("webhook_url")
    if not webhook_url:
        return

    icons = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
    icon = icons.get(notification["type"], "ℹ️")

    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json={
            "msgtype": "text",
            "text": {
                "content": f"{icon} {notification['title']}\n{notification['message']}"
            }
        })


async def push_feishu(notification: dict, config: dict):
    """飞书 Webhook"""
    import httpx

    webhook_url = config.get("webhook_url")
    if not webhook_url:
        return

    icons = {"success": "✅", "warning": "⚠️", "error": "❌", "info": "ℹ️"}
    icon = icons.get(notification["type"], "ℹ️")

    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json={
            "msg_type": "text",
            "content": {
                "text": f"{icon} {notification['title']}\n{notification['message']}"
            }
        })


# ============== FastAPI 应用 ==============

app = FastAPI(title="通知系统 API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()
    # 启动定时调度器（每 30 秒检查一次）
    asyncio.create_task(scheduler.run_scheduler(manager, push_to_channels, interval=30))


# ============== WebSocket ==============

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # 发送历史通知
        notifications = await notification_storage.get_all(limit=50)
        await websocket.send_json({
            "type": "history",
            "data": notifications
        })

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============== 通知 API ==============

@app.get("/")
async def root():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_path = os.path.join(base_dir, "..", "frontend", "index.html")
    return FileResponse(frontend_path)


@app.get("/api/notifications")
async def get_notifications(
    limit: int = 50,
    category: Optional[str] = None,
    type_: Optional[str] = None,
    unread_only: bool = False
):
    return await notification_storage.get_all(limit, category, type_, unread_only)


@app.post("/api/notifications")
async def create_notification(notification: NotificationCreate):
    n = {
        "id": str(uuid.uuid4()),
        "title": notification.title,
        "message": notification.message,
        "type": notification.type.value,
        "category": notification.category,
        "tags": notification.tags,
        "duration": notification.duration,
        "timestamp": datetime.now().isoformat(),
    }
    await notification_storage.add(n)

    # 广播给所有 WebSocket 客户端
    await manager.broadcast({"type": "new", "data": n})

    # 推送到订阅渠道
    await push_to_channels(n)

    return n


@app.patch("/api/notifications/{notification_id}/read")
async def mark_read(notification_id: str):
    if not await notification_storage.mark_read(notification_id):
        raise HTTPException(status_code=404, detail="通知不存在")
    return {"status": "ok"}


@app.post("/api/notifications/read-all")
async def mark_all_read():
    count = await notification_storage.mark_all_read()
    await manager.broadcast({"type": "read_all"})
    return {"count": count}


@app.delete("/api/notifications/{notification_id}")
async def delete_notification(notification_id: str):
    if not await notification_storage.delete(notification_id):
        raise HTTPException(status_code=404, detail="通知不存在")
    await manager.broadcast({"type": "deleted", "id": notification_id})
    return {"status": "ok"}


@app.delete("/api/notifications")
async def clear_notifications():
    count = await notification_storage.clear()
    await manager.broadcast({"type": "cleared"})
    return {"count": count}


@app.get("/api/stats")
async def get_stats():
    return await notification_storage.get_stats()


# ============== 定时调度 API ==============

@app.get("/api/notifications/scheduled")
async def get_scheduled_notifications(status: Optional[str] = None):
    """获取所有定时通知，可按状态筛选 (pending/sent/cancelled)"""
    scheduled = await notification_storage.get_scheduled(status)
    return APIResponse.success(scheduled)


@app.get("/api/notifications/scheduled/pending")
async def get_pending_scheduled():
    """获取所有已到期但未发送的定时通知"""
    pending = await notification_storage.get_pending_scheduled()
    return APIResponse.success(pending)


@app.post("/api/notifications/{notification_id}/cancel")
async def cancel_scheduled_notification(notification_id: str):
    """取消定时通知"""
    cancelled = await notification_storage.cancel_scheduled(notification_id)
    if not cancelled:
        raise AppException(ErrorCode.ERR_SCHEDULED_NOT_FOUND, f"通知 {notification_id} 不存在或无法取消")
    await manager.broadcast({"type": "cancelled", "id": notification_id})
    return APIResponse.success(message="定时通知已取消")


# ============== 分类 API ==============

@app.get("/api/categories")
async def get_categories():
    """获取所有分类"""
    stats = await notification_storage.get_stats()
    categories = list(stats.get("by_category", {}).keys())
    if "general" not in categories:
        categories.insert(0, "general")
    return categories


# ============== 模板 API ==============

@app.get("/api/templates")
async def get_templates():
    return await template_storage.get_all()


@app.post("/api/templates")
async def create_template(template: TemplateCreate):
    t = {
        "id": str(uuid.uuid4()),
        "name": template.name,
        "title": template.title,
        "message": template.message,
        "type": template.type.value,
        "category": template.category,
        "variables": template.variables,
        "created_at": datetime.now().isoformat(),
    }
    return await template_storage.add(t)


@app.get("/api/templates/{template_id}")
async def get_template(template_id: str):
    template = await template_storage.get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    return template


@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: str):
    if not await template_storage.delete(template_id):
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"status": "ok"}


# ============== 用户认证 API ==============

@app.post("/api/auth/register")
async def register(user: UserCreate):
    # 检查用户名是否存在
    existing = await user_storage.get_by_username(user.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    from passlib.hash import bcrypt
    new_user = {
        "id": str(uuid.uuid4()),
        "username": user.username,
        "password_hash": bcrypt.hash(user.password),
        "email": user.email,
        "created_at": datetime.now().isoformat(),
    }
    await user_storage.create(new_user)

    token = create_token(new_user["id"], new_user["username"])
    return {"token": token, "user_id": new_user["id"], "username": new_user["username"]}


@app.post("/api/auth/login")
async def login(login_req: LoginRequest):
    user = await user_storage.get_by_username(login_req.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    from passlib.hash import bcrypt
    if not bcrypt.verify(login_req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_token(user["id"], user["username"])
    return {"token": token, "user_id": user["id"], "username": user["username"]}


# ============== API Keys API ==============

@app.get("/api/keys")
async def get_api_keys():
    """获取所有 API Keys (简化版，不返回 key 本身)"""
    keys = await apikey_storage.get_all()
    return [{"id": k["id"], "name": k["name"], "permissions": k["permissions"],
             "created_at": k["created_at"], "last_used": k.get("last_used")} for k in keys]


@app.post("/api/keys")
async def create_api_key(key_req: APIKeyCreate):
    key = secrets.token_urlsafe(32)
    new_key = {
        "id": str(uuid.uuid4()),
        "key": key,
        "name": key_req.name,
        "permissions": key_req.permissions,
        "created_at": datetime.now().isoformat(),
    }
    await apikey_storage.create(new_key)
    return {"id": new_key["id"], "key": key, "name": new_key["name"], "permissions": new_key["permissions"]}


@app.delete("/api/keys/{key_id}")
async def delete_api_key(key_id: str):
    if not await apikey_storage.delete(key_id):
        raise HTTPException(status_code=404, detail="API Key 不存在")
    return {"status": "ok"}


# ============== 订阅 API ==============

@app.get("/api/subscriptions")
async def get_subscriptions():
    return await subscription_storage.get_all()


@app.post("/api/subscriptions")
async def create_subscription(sub: SubscriptionCreate):
    new_sub = {
        "id": str(uuid.uuid4()),
        "channel": sub.channel,
        "config": sub.config,
        "types": sub.types,
        "categories": sub.categories,
        "created_at": datetime.now().isoformat(),
    }
    return await subscription_storage.create(new_sub)


@app.delete("/api/subscriptions/{sub_id}")
async def delete_subscription(sub_id: str):
    if not await subscription_storage.delete(sub_id):
        raise HTTPException(status_code=404, detail="订阅不存在")
    return {"status": "ok"}


# ============== 启动 ==============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)