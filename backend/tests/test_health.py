"""
文件职责：
该文件负责测试系统健康检查接口。

所属功能：
服务监控与存活检测。

主要流程：
调用 /api/v1/health 接口，验证返回状态、服务名称以及必需的响应头（如 x-request-id）。
"""

import importlib

import pytest
from fastapi.testclient import TestClient


def test_health_endpoint_returns_service_status_and_request_id() -> None:
    """
    测试健康检查端点是否正常返回服务状态及请求 ID。

    模拟请求健康检查 API 并验证响应格式及相关的 Headers，以证明服务可以正常接收并处理请求。
    """
    try:
        # 尝试动态加载 app.main 模块以获取 FastAPI 应用实例。
        # 如果尚未实现，提前主动导致测试失败并给出清晰提示。
        module = importlib.import_module("app.main")
    except ModuleNotFoundError:
        pytest.fail("app.main has not been implemented")

    # 使用获取到的应用对象创建 TestClient 并直接发起 GET 请求访问健康检查接口。
    response = TestClient(module.app).get("/api/v1/health")

    # 断言 HTTP 状态码是否为表示成功的 200。
    assert response.status_code == 200
    # 断言响应的 JSON 数据体是否包含预期的状态信息以及服务名称。
    assert response.json() == {"status": "ok", "service": "小米智能客服机器人"}
    # 验证响应头中是否注入了 `x-request-id`，这是服务链路追踪的重要标识。
    assert response.headers["x-request-id"]
