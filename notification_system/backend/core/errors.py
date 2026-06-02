"""
统一错误码定义
所有错误码格式: ERR_{模块}_{编号}
"""

from enum import Enum
from typing import Optional


class ErrorCode(str, Enum):
    # 通用错误 (1000-1999)
    SUCCESS = "SUCCESS"  # 成功
    ERR_UNKNOWN = "ERR_UNKNOWN"  # 未知错误
    ERR_VALIDATION = "ERR_VALIDATION"  # 参数校验失败
    ERR_NOT_FOUND = "ERR_NOT_FOUND"  # 资源不存在
    ERR_DUPLICATE = "ERR_DUPLICATE"  # 资源重复
    ERR_PERMISSION = "ERR_PERMISSION"  # 权限不足
    ERR_TIMEOUT = "ERR_TIMEOUT"  # 操作超时
    ERR_INTERNAL = "ERR_INTERNAL"  # 内部错误

    # 认证模块 (2000-2999)
    ERR_AUTH_TOKEN_INVALID = "ERR_AUTH_TOKEN_INVALID"  # Token 无效
    ERR_AUTH_TOKEN_EXPIRED = "ERR_AUTH_TOKEN_EXPIRED"  # Token 过期
    ERR_AUTH_CREDENTIALS = "ERR_AUTH_CREDENTIALS"  # 凭证错误
    ERR_AUTH_USER_EXISTS = "ERR_AUTH_USER_EXISTS"  # 用户已存在
    ERR_AUTH_USER_NOT_FOUND = "ERR_AUTH_USER_NOT_FOUND"  # 用户不存在

    # 通知模块 (3000-3999)
    ERR_NOTIFICATION_NOT_FOUND = "ERR_NOTIFICATION_NOT_FOUND"  # 通知不存在
    ERR_NOTIFICATION_CREATE_FAILED = "ERR_NOTIFICATION_CREATE_FAILED"  # 创建通知失败
    ERR_NOTIFICATION_DELETE_FAILED = "ERR_NOTIFICATION_DELETE_FAILED"  # 删除通知失败

    # 模板模块 (4000-4999)
    ERR_TEMPLATE_NOT_FOUND = "ERR_TEMPLATE_NOT_FOUND"  # 模板不存在
    ERR_TEMPLATE_CREATE_FAILED = "ERR_TEMPLATE_CREATE_FAILED"  # 创建模板失败
    ERR_TEMPLATE_DELETE_FAILED = "ERR_TEMPLATE_DELETE_FAILED"  # 删除模板失败

    # 订阅模块 (5000-5999)
    ERR_SUBSCRIPTION_NOT_FOUND = "ERR_SUBSCRIPTION_NOT_FOUND"  # 订阅不存在
    ERR_SUBSCRIPTION_CREATE_FAILED = "ERR_SUBSCRIPTION_CREATE_FAILED"  # 创建订阅失败
    ERR_SUBSCRIPTION_CHANNEL_ERROR = "ERR_SUBSCRIPTION_CHANNEL_ERROR"  # 渠道配置错误

    # API Key 模块 (6000-6999)
    ERR_APIKEY_NOT_FOUND = "ERR_APIKEY_NOT_FOUND"  # API Key 不存在
    ERR_APIKEY_CREATE_FAILED = "ERR_APIKEY_CREATE_FAILED"  # 创建 API Key 失败
    ERR_APIKEY_INVALID = "ERR_APIKEY_INVALID"  # API Key 无效

    # 推送模块 (7000-7999)
    ERR_PUSH_DESKTOP_FAILED = "ERR_PUSH_DESKTOP_FAILED"  # 桌面推送失败
    ERR_PUSH_EMAIL_FAILED = "ERR_PUSH_EMAIL_FAILED"  # 邮件推送失败
    ERR_PUSH_DINGTALK_FAILED = "ERR_PUSH_DINGTALK_FAILED"  # 钉钉推送失败
    ERR_PUSH_FEISHU_FAILED = "ERR_PUSH_FEISHU_FAILED"  # 飞书推送失败

    # 调度模块 (8000-8999)
    ERR_SCHEDULED_NOT_FOUND = "ERR_SCHEDULED_NOT_FOUND"  # 定时通知不存在
    ERR_SCHEDULED_ALREADY_SENT = "ERR_SCHEDULED_ALREADY_SENT"  # 定时通知已发送
    ERR_SCHEDULED_TIME_INVALID = "ERR_SCHEDULED_TIME_INVALID"  # 定时时间无效


class APIResponse:
    """统一响应格式"""
    
    @staticmethod
    def success(data=None, message: str = "操作成功") -> dict:
        return {
            "code": 0,
            "message": message,
            "data": data
        }
    
    @staticmethod
    def error(code: ErrorCode, message: Optional[str] = None, detail: Optional[dict] = None) -> dict:
        return {
            "code": code.value,
            "message": message or code.name,
            "detail": detail
        }
    
    @staticmethod
    def paginated(data: list, total: int, page: int = 1, page_size: int = 20) -> dict:
        return {
            "code": 0,
            "message": "success",
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }


# 错误码到 HTTP 状态码映射
ERROR_CODE_HTTP_STATUS = {
    ErrorCode.SUCCESS: 200,
    ErrorCode.ERR_VALIDATION: 400,
    ErrorCode.ERR_DUPLICATE: 409,
    ErrorCode.ERR_PERMISSION: 403,
    ErrorCode.ERR_NOT_FOUND: 404,
    ErrorCode.ERR_NOTIFICATION_NOT_FOUND: 404,
    ErrorCode.ERR_TEMPLATE_NOT_FOUND: 404,
    ErrorCode.ERR_SUBSCRIPTION_NOT_FOUND: 404,
    ErrorCode.ERR_APIKEY_NOT_FOUND: 404,
    ErrorCode.ERR_SCHEDULED_NOT_FOUND: 404,
    ErrorCode.ERR_SCHEDULED_ALREADY_SENT: 409,
    ErrorCode.ERR_AUTH_TOKEN_INVALID: 401,
    ErrorCode.ERR_AUTH_TOKEN_EXPIRED: 401,
    ErrorCode.ERR_AUTH_CREDENTIALS: 401,
    ErrorCode.ERR_INTERNAL: 500,
}