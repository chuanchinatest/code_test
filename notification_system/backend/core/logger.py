"""
统一日志采集
支持多级别、多输出、请求追踪
"""

import logging
import json
import sys
import traceback
from datetime import datetime
from typing import Optional, Any
from contextvars import ContextVar
from functools import wraps
import uuid

# 请求追踪 ID
request_id_var: ContextVar[str] = ContextVar('request_id', default='')


class JSONFormatter(logging.Formatter):
    """JSON 格式日志"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get() or None,
        }
        
        # 添加额外字段
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data, ensure_ascii=False)


class TextFormatter(logging.Formatter):
    """人类可读格式日志"""
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        request_id = request_id_var.get()
        req_id_str = f"[{request_id[:8]}]" if request_id else ""
        return f"{timestamp} {record.levelname:7} {req_id_str} {record.name}: {record.getMessage()}"


class LogCollector:
    """日志收集器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.loggers = {}
    
    def setup_logger(
        self,
        name: str,
        level: int = logging.INFO,
        json_format: bool = False,
        file_path: Optional[str] = None
    ) -> logging.Logger:
        """配置日志器"""
        if name in self.loggers:
            return self.loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.handlers.clear()
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(
            JSONFormatter() if json_format else TextFormatter()
        )
        logger.addHandler(console_handler)
        
        # 文件处理器
        if file_path:
            file_handler = logging.FileHandler(file_path, encoding='utf-8')
            file_handler.setLevel(level)
            file_handler.setFormatter(JSONFormatter())
            logger.addHandler(file_handler)
        
        self.loggers[name] = logger
        return logger
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取日志器"""
        if name not in self.loggers:
            return self.setup_logger(name)
        return self.loggers[name]


# 全局日志收集器
collector = LogCollector()

# 预配置的日志器
def get_logger(name: str = "notification") -> logging.Logger:
    """获取日志器"""
    return collector.get_logger(name)


def log_request(logger: logging.Logger):
    """请求日志装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request_id = str(uuid.uuid4())
            request_id_var.set(request_id)
            
            logger.info(f"请求开始", extra={
                "function": func.__name__,
                "request_id": request_id
            })
            
            try:
                result = await func(*args, **kwargs)
                logger.info(f"请求完成", extra={
                    "function": func.__name__,
                    "request_id": request_id
                })
                return result
            except Exception as e:
                logger.error(f"请求失败: {str(e)}", extra={
                    "function": func.__name__,
                    "request_id": request_id
                }, exc_info=True)
                raise
        
        return wrapper
    return decorator


class LogMiddleware:
    """日志中间件"""
    
    def __init__(self, app, logger: logging.Logger):
        self.app = app
        self.logger = logger
    
    async def __call__(self, scope, receive, send):
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        # 记录请求开始
        self.logger.info(f"--> {scope['method']} {scope['path']}", extra={
            "request_id": request_id,
            "method": scope['method'],
            "path": scope['path'],
            "client": scope.get('client')
        })
        
        # 处理请求
        await self.app(scope, receive, send)
        
        # 记录请求结束
        self.logger.info(f"<-- {scope['method']} {scope['path']}", extra={
            "request_id": request_id
        })


# 便捷日志函数
def log_info(message: str, **kwargs):
    get_logger().info(message, extra=kwargs)

def log_error(message: str, **kwargs):
    get_logger().error(message, extra=kwargs)

def log_warning(message: str, **kwargs):
    get_logger().warning(message, extra=kwargs)

def log_debug(message: str, **kwargs):
    get_logger().debug(message, extra=kwargs)