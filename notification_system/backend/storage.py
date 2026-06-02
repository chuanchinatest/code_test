"""
数据库存储层 - SQLite + aiosqlite
"""

import aiosqlite
import json
from datetime import datetime
from typing import Optional, List
from pathlib import Path


DB_PATH = Path(__file__).parent / "notifications.db"


async def init_db():
    """初始化数据库"""
    async with aiosqlite.connect(DB_PATH) as db:
        # 通知表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'info',
                category TEXT DEFAULT 'general',
                tags TEXT DEFAULT '[]',
                duration REAL DEFAULT 5.0,
                read INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                user_id TEXT,
                scheduled_at TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        # 添加新字段（如果不存在）
        for col, col_type in [("scheduled_at", "TEXT"), ("status", "TEXT DEFAULT 'pending'")]:
            try:
                await db.execute(f"ALTER TABLE notifications ADD COLUMN {col} {col_type}")
            except Exception:
                pass

        # 模板表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'info',
                category TEXT DEFAULT 'general',
                variables TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                user_id TEXT
            )
        """)

        # 用户表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # API Keys 表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                key TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                user_id TEXT,
                permissions TEXT DEFAULT '["read"]',
                created_at TEXT NOT NULL,
                last_used TEXT
            )
        """)

        # 订阅表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                channel TEXT NOT NULL,
                config TEXT NOT NULL,
                types TEXT DEFAULT '[]',
                categories TEXT DEFAULT '[]',
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)

        await db.commit()


class NotificationStorage:
    """通知存储"""

    def __init__(self):
        self.db_path = str(DB_PATH)

    async def add(self, notification: dict) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO notifications (id, title, message, type, category, tags, duration, read, created_at, user_id, scheduled_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                notification["id"],
                notification["title"],
                notification["message"],
                notification.get("type", "info"),
                notification.get("category", "general"),
                json.dumps(notification.get("tags", [])),
                notification.get("duration", 5.0),
                0,
                notification["timestamp"],
                notification.get("user_id"),
                notification.get("scheduled_at"),
                notification.get("status", "pending")
            ))
            await db.commit()
        return notification

    async def get_all(self, limit: int = 50, category: Optional[str] = None, 
                      type_: Optional[str] = None, unread_only: bool = False) -> List[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM notifications WHERE 1=1"
            params = []

            if category:
                query += " AND category = ?"
                params.append(category)
            if type_:
                query += " AND type = ?"
                params.append(type_)
            if unread_only:
                query += " AND read = 0"

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def mark_read(self, notification_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE notifications SET read = 1 WHERE id = ?", (notification_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def mark_all_read(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("UPDATE notifications SET read = 1 WHERE read = 0")
            await db.commit()
            return cursor.rowcount

    async def delete(self, notification_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM notifications WHERE id = ?", (notification_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def clear(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM notifications")
            row = await cursor.fetchone()
            count = row[0] if row else 0
            await db.execute("DELETE FROM notifications")
            await db.commit()
            return count

    async def get_stats(self) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # 总数
            cursor = await db.execute("SELECT COUNT(*) as count FROM notifications")
            total = (await cursor.fetchone())["count"]

            # 未读数
            cursor = await db.execute("SELECT COUNT(*) as count FROM notifications WHERE read = 0")
            unread = (await cursor.fetchone())["count"]

            # 按类型统计
            by_type = {}
            for type_ in ["success", "warning", "error", "info"]:
                cursor = await db.execute(
                    "SELECT COUNT(*) as count FROM notifications WHERE type = ?", (type_,)
                )
                by_type[type_] = (await cursor.fetchone())["count"]

            # 按分类统计
            by_category = {}
            cursor = await db.execute("SELECT category, COUNT(*) as count FROM notifications GROUP BY category")
            for row in await cursor.fetchall():
                by_category[row["category"]] = row["count"]

            # 每日统计 (最近 7 天)
            daily = []
            for i in range(7):
                date = (datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).timestamp() - i * 86400
                cursor = await db.execute("""
                    SELECT COUNT(*) as count FROM notifications 
                    WHERE created_at >= ? AND created_at < ?
                """, (date, date + 86400))
                row = await cursor.fetchone()
                daily.append({
                    "date": datetime.fromtimestamp(date).strftime("%m-%d"),
                    "count": row["count"] if row else 0
                })

            return {
                "total": total,
                "unread": unread,
                "by_type": by_type,
                "by_category": by_category,
                "daily": list(reversed(daily))
            }

    async def get_scheduled(self, status: Optional[str] = None) -> List[dict]:
        """获取所有定时通知，可按状态筛选"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT * FROM notifications WHERE scheduled_at IS NOT NULL"
            params = []
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY scheduled_at ASC"
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_pending_scheduled(self) -> List[dict]:
        """获取所有已到期但未发送的定时通知"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            now = datetime.now().isoformat()
            cursor = await db.execute("""
                SELECT * FROM notifications 
                WHERE scheduled_at IS NOT NULL 
                AND status = 'pending'
                AND scheduled_at <= ?
                ORDER BY scheduled_at ASC
            """, (now,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_status(self, notification_id: str, status: str) -> bool:
        """更新通知状态"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE notifications SET status = ? WHERE id = ?", (status, notification_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def cancel_scheduled(self, notification_id: str) -> bool:
        """取消定时通知"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE notifications SET status = 'cancelled' WHERE id = ? AND status = 'pending'", 
                (notification_id,)
            )
            await db.commit()
            return cursor.rowcount > 0


class TemplateStorage:
    """模板存储"""

    def __init__(self):
        self.db_path = str(DB_PATH)

    async def add(self, template: dict) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO templates (id, name, title, message, type, category, variables, created_at, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template["id"],
                template["name"],
                template["title"],
                template["message"],
                template.get("type", "info"),
                template.get("category", "general"),
                json.dumps(template.get("variables", [])),
                template["created_at"],
                template.get("user_id")
            ))
            await db.commit()
        return template

    async def get_all(self) -> List[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM templates ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get(self, template_id: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def delete(self, template_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM templates WHERE id = ?", (template_id,))
            await db.commit()
            return cursor.rowcount > 0


class UserStorage:
    """用户存储"""

    def __init__(self):
        self.db_path = str(DB_PATH)

    async def create(self, user: dict) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO users (id, username, password_hash, email, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user["id"],
                user["username"],
                user["password_hash"],
                user.get("email"),
                user["created_at"]
            ))
            await db.commit()
        return user

    async def get_by_username(self, username: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_by_id(self, user_id: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None


class APIKeyStorage:
    """API Key 存储"""

    def __init__(self):
        self.db_path = str(DB_PATH)

    async def create(self, api_key: dict) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO api_keys (id, key, name, user_id, permissions, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                api_key["id"],
                api_key["key"],
                api_key["name"],
                api_key.get("user_id"),
                json.dumps(api_key.get("permissions", ["read"])),
                api_key["created_at"]
            ))
            await db.commit()
        return api_key

    async def get_by_key(self, key: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM api_keys WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_last_used(self, key: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE api_keys SET last_used = ? WHERE key = ?",
                (datetime.now().isoformat(), key)
            )
            await db.commit()

    async def get_all(self) -> List[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM api_keys ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def delete(self, key_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
            await db.commit()
            return cursor.rowcount > 0


class SubscriptionStorage:
    """订阅存储"""

    def __init__(self):
        self.db_path = str(DB_PATH)

    async def create(self, subscription: dict) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO subscriptions (id, user_id, channel, config, types, categories, active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subscription["id"],
                subscription.get("user_id"),
                subscription["channel"],
                json.dumps(subscription["config"]),
                json.dumps(subscription.get("types", [])),
                json.dumps(subscription.get("categories", [])),
                1,
                subscription["created_at"]
            ))
            await db.commit()
        return subscription

    async def get_all(self) -> List[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM subscriptions WHERE active = 1")
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def delete(self, sub_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("UPDATE subscriptions SET active = 0 WHERE id = ?", (sub_id,))
            await db.commit()
            return cursor.rowcount > 0