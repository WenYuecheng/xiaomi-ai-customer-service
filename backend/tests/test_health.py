import importlib

import pytest
from fastapi.testclient import TestClient


def test_health_endpoint_returns_service_status_and_request_id() -> None:
    try:
        module = importlib.import_module("app.main")
    except ModuleNotFoundError:
        pytest.fail("app.main has not been implemented")

    response = TestClient(module.app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "小米智能客服机器人"}
    assert response.headers["x-request-id"]
