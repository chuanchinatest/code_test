"""
定时通知调度器
定期检查并发送到期的定时通知
"""

import asyncio
import logging
from datetime import datetime

from storage import NotificationStorage

logger = logging.getLogger("scheduler")

notification_storage = NotificationStorage()


async def check_and_send_scheduled(manager, push_to_channels_func):
    """
    检查并发送到期的定时通知
    
    Args:
        manager: WebSocket ConnectionManager 实例
        push_to_channels_func: 推送函数
    """
    try:
        pending = await notification_storage.get_pending_scheduled()
        now = datetime.now().isoformat()
        
        if pending:
            logger.info(f"发现 {len(pending)} 条待发送的定时通知")
        
        for notif in pending:
            try:
                # 发送通知
                await manager.broadcast({"type": "new", "data": notif})
                await push_to_channels_func(notif)
                
                # 更新状态为已发送
                await notification_storage.update_status(notif["id"], "sent")
                
                logger.info(
                    f"定时通知已发送", 
                    extra={"notification_id": notif["id"], "title": notif["title"]}
                )
            except Exception as e:
                logger.error(
                    f"定时通知发送失败", 
                    extra={"notification_id": notif["id"], "error": str(e)}
                )
    except Exception as e:
        logger.error(f"调度器检查失败", extra={"error": str(e)})


async def run_scheduler(manager, push_to_channels_func, interval: int = 30):
    """
    启动定时调度器
    
    Args:
        manager: WebSocket ConnectionManager 实例
        push_to_channels_func: 推送函数
        interval: 检查间隔（秒），默认 30 秒
    """
    logger.info(f"定时调度器已启动，检查间隔: {interval}秒")
    
    while True:
        try:
            await check_and_send_scheduled(manager, push_to_channels_func)
        except Exception as e:
            logger.error(f"调度器异常", extra={"error": str(e)})
        
        await asyncio.sleep(interval)
