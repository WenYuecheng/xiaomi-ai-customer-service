"""
文件职责：
该文件负责定义系统的 HTTP 中间件组件。

所属功能：
核心基础设施 -> HTTP 中间件。

主要流程：
拦截所有进来的 HTTP 请求，在传递给具体路由前执行处理逻辑（如注入 request_id）。

主要调用方：
被 `main.py` 在初始化应用时挂载。
"""

from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    主要职责：
    为每个请求生成全局唯一的 `x-request-id`，便于全链路日志追踪和错误定位。
    如果客户端在 Headers 传入了该字段，则沿用客户端的，否则自动生成。
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response
