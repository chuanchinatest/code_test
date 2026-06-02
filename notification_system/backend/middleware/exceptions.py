"""
统一异常处理
"""

from typing import Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError

from core.errors import ErrorCode, APIResponse, ERROR_CODE_HTTP_STATUS


class AppException(Exception):
    """应用异常"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: Optional[str] = None,
        detail: Optional[dict] = None
    ):
        self.code = code
        self.message = message or code.name
        self.detail = detail
        super().__init__(self.message)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """应用异常处理"""
    from core.logger import get_logger
    logger = get_logger()
    
    logger.error(f"应用异常: {exc.code} - {exc.message}", extra={
        "code": exc.code.value,
        "detail": exc.detail,
        "path": request.url.path
    })
    
    http_status = ERROR_CODE_HTTP_STATUS.get(exc.code, 500)
    return JSONResponse(
        status_code=http_status,
        content=APIResponse.error(exc.code, exc.message, exc.detail)
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """参数校验异常处理"""
    from core.logger import get_logger
    logger = get_logger()
    
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(f"参数校验失败: {errors}", extra={
        "path": request.url.path,
        "errors": errors
    })
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=APIResponse.error(
            ErrorCode.ERR_VALIDATION,
            "参数校验失败",
            {"errors": errors}
        )
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """HTTP 异常处理"""
    from core.logger import get_logger
    logger = get_logger()
    
    logger.warning(f"HTTP 异常: {exc.status_code} - {exc.detail}", extra={
        "path": request.url.path,
        "status_code": exc.status_code
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "detail": None
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理"""
    from core.logger import get_logger
    logger = get_logger()
    
    logger.error(f"未处理异常: {str(exc)}", extra={
        "path": request.url.path,
        "exception": str(exc),
        "type": type(exc).__name__
    }, exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=APIResponse.error(
            ErrorCode.ERR_INTERNAL,
            "服务器内部错误"
        )
    )


def register_exception_handlers(app):
    """注册异常处理器"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)