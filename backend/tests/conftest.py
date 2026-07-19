"""
文件职责：
该文件负责提供 Pytest 测试框架的全局 fixture。

所属功能：
后端测试基础设施。

主要流程：
定义并初始化测试环境的配置、FastAPI 应用实例、测试客户端以及测试用户数据，供各个测试用例使用。
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """
    提供测试环境的配置实例。

    Args:
        tmp_path (Path): Pytest 提供的临时目录路径，用于存放测试过程中的临时文件。

    Returns:
        Settings: 初始化好的应用配置实例，包含测试用的数据库路径、上传目录等。
    """
    # 初始化配置对象，并指定专为测试配置的路径与 Mock 参数，避免对真实环境造成影响。
    return Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        upload_dir=tmp_path / "uploads",
        chroma_dir=tmp_path / "chroma",
        model_artifact_dir=tmp_path / "models",
        jwt_secret="test-secret-with-at-least-thirty-two-characters",  # noqa: S106
        llm_provider="mock",
        llm_model="mock-grounded-chat",
        embedding_provider="mock",
        embedding_model="mock-hash-embedding",
    )


@pytest.fixture
def application(settings: Settings) -> FastAPI:
    """
    提供 FastAPI 应用实例。

    Args:
        settings (Settings): 依赖的测试配置实例。

    Returns:
        FastAPI: 创建好的 FastAPI 应用对象。
    """
    # 延迟导入以防止应用初始化时配置尚未准备好。
    from app.main import create_app

    # 使用测试配置创建并返回 FastAPI 实例。
    return create_app(settings)


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    """
    提供基于 TestClient 的 API 测试客户端。

    Args:
        application (FastAPI): 依赖的 FastAPI 应用实例。

    Returns:
        Iterator[TestClient]: FastAPI 的 TestClient 生成器。
    """
    # 使用上下文管理器实例化 TestClient，以便在 yield 之后正确处理清理逻辑。
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def users(application: FastAPI) -> dict[str, str]:
    """
    创建初始测试用户，并返回用户名与密码的映射字典。

    Args:
        application (FastAPI): 依赖的 FastAPI 应用实例。

    Returns:
        dict[str, str]: 包含测试用户名及对应密码的字典。
    """
    from app.auth.service import create_user

    # 从应用状态中获取数据库会话工厂，用于操作测试数据库。
    session_factory = application.state.session_factory
    # 建立数据库会话上下文。
    with session_factory() as session:
        # 分别创建拥有不同角色权限的用户，满足不同测试用例的需要。
        create_user(session, "admin", "AdminPass123!", "admin")
        create_user(session, "operator", "OperatorPass123!", "operator")
        create_user(session, "customer", "CustomerPass123!", "user")
    return {
        "admin": "AdminPass123!",
        "operator": "OperatorPass123!",
        "customer": "CustomerPass123!",
    }


def auth_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    """
    模拟用户登录并生成带有 Authorization 的请求头字典。

    Args:
        client (TestClient): API 测试客户端。
        username (str): 登录用户名。
        password (str): 登录密码。

    Returns:
        dict[str, str]: 包含 Bearer Token 的 Authorization 字典，用于需要认证的请求。

    Raises:
        AssertionError: 当登录请求返回的 HTTP 状态码不是 200 时。
    """
    # 发送登录请求，提交用户名和密码表单数据以换取 access token。
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    # 断言登录必须成功，否则附带错误信息抛出异常。
    assert response.status_code == 200, response.text
    # 解析响应中的 JWT 并构造认证请求头。
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
