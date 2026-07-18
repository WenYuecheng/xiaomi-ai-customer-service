"""
文件职责：
该文件负责定义全系统的标准业务异常和全局错误处理机制。

所属功能：
核心基础设施 -> 异常处理。

主要流程：
1. 提供 `AppError` 基础异常类，供业务层抛出特定的错误状态码和错误码。
2. 注册 FastApi 异常处理器，将未捕获的 `AppError` 和请求校验错误
   `RequestValidationError` 转换为标准 JSON 响应结构。

主要调用方：
整个系统各层级代码（如 Service 层、Controller 层）均可抛出 `AppError`。
被 `main.py` 挂载为 FastAPI 全局异常处理器。

副作用：
拦截请求并提前返回 HTTP 响应。
"""

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """
    主要职责：
    标准业务异常基类。业务层遇到校验不通过或逻辑限制时，主动抛出此异常，而非直接返回响应对象。

    所属功能：
    核心基础设施 -> 异常处理。

    协作关系：
    被业务层抛出，最终被 `app_error_handler` 捕获。
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def error_payload(request: Request, code: str, message: str, details: Any | None = None) -> dict:
    """
    内部辅助函数：构造统一格式的错误响应体。包含从 request state 提取的 request_id，方便日志追溯。
    """
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", None),
            "details": details,
        }
    }


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """
    功能归属：
    核心基础设施 -> 异常处理。

    函数职责：
    全局捕获由业务代码抛出的 `AppError` 异常，并转换为对应的 HTTP 状态码和标准 JSON 响应。
    属于系统内部错误、业务规则错误。
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload(request, exc.code, exc.message, exc.details),
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    功能归属：
    核心基础设施 -> 异常处理。

    函数职责：
    全局捕获 FastAPI 路由参数、Body 校验失败时抛出的 `RequestValidationError`。
    属于用户输入错误。

    数据转换：
    提取 Pydantic 提供的错误位置、提示信息，转换为前端友好的 details 数组，并统一返回 422 状态码。
    """
    details = [
        {"location": list(error["loc"]), "message": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_payload(request, "validation_error", "请求参数不合法", details),
    )
