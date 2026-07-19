"""
文件职责：
该文件负责测试用户认证登录及基于角色的知识库管理权限控制。

所属功能：
用户登录与知识库权限 (Login & Knowledge Base Permissions)

主要流程：
1. 测试有效用户的登录及 Token 获取。
2. 测试无效密码登录被拒绝。
3. 测试不同角色（如操作员、普通用户）对知识库资源的访问与操作控制。
"""

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_login_and_me_return_verified_user(client: TestClient, users: dict[str, str]) -> None:
    """
    测试用户可以通过登录获取验证，并通过 `/me` 接口返回脱敏后的自身信息。

    Args:
        client: 测试客户端，用于发送 HTTP 请求。
        users: fixtures 提供的一组初始用户数据（包含用户名和密码映射）。

    Returns:
        None

    Raises:
        AssertionError: 如果响应状态码不是 200，或者返回的数据中包含敏感信息（如密码哈希）。
    """
    # 使用 admin 用户生成请求头用于验证
    headers = auth_headers(client, "admin", users["admin"])

    response = client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["role"] == "admin"
    assert "password_hash" not in response.json()


def test_invalid_password_is_rejected(client: TestClient, users: dict[str, str]) -> None:
    """
    测试提供错误密码时登录接口能够正确予以拒绝并返回相应错误码。

    Args:
        client: 测试客户端。
        users: fixtures 提供的初始用户数据。

    Returns:
        None

    Raises:
        AssertionError: 如果响应状态码不等于 401 或错误码不匹配。
    """
    # 发送错误的凭证信息以尝试登录
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_operator_can_create_and_filter_knowledge_bases(
    client: TestClient, users: dict[str, str]
) -> None:
    """
    测试操作员（Operator）角色能够成功创建知识库并通过过滤条件查询知识库列表。

    Args:
        client: 测试客户端。
        users: 包含用户数据的字典，用于获取 operator 的凭证。

    Returns:
        None

    Raises:
        AssertionError: 如果无法正确创建知识库，或者列表查询未能返回刚创建的对象。
    """
    # 模拟以 operator 角色登录获取访问权限
    headers = auth_headers(client, "operator", users["operator"])
    created = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "手机产品", "description": "手机说明书与规格"},
    )

    response = client.get("/api/v1/knowledge-bases?q=手机", headers=headers)

    assert created.status_code == 201
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["name"] == "手机产品"
    assert response.json()["items"][0]["status"] == "active"


def test_regular_user_cannot_manage_knowledge_bases(
    client: TestClient, users: dict[str, str]
) -> None:
    """
    测试普通用户（Customer）由于权限不足，无法管理（如创建）知识库。

    Args:
        client: 测试客户端。
        users: 包含用户数据的字典，用于获取 customer 的凭证。

    Returns:
        None

    Raises:
        AssertionError: 如果接口未拦截越权操作并返回状态码 403。
    """
    # 构造普通用户的身份令牌
    headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/knowledge-bases",
        headers=headers,
        json={"name": "越权知识库"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_duplicate_knowledge_base_name_returns_conflict(
    client: TestClient, users: dict[str, str]
) -> None:
    """
    测试创建名称已存在的知识库时，系统能够有效拦截并返回冲突（Conflict）错误。

    Args:
        client: 测试客户端。
        users: 包含用户数据的字典，用于获取 operator 的凭证。

    Returns:
        None

    Raises:
        AssertionError: 响应不是 409 Conflict 或者错误码信息不符。
    """
    headers = auth_headers(client, "operator", users["operator"])
    payload = {"name": "重复名称"}
    assert client.post("/api/v1/knowledge-bases", headers=headers, json=payload).status_code == 201

    response = client.post("/api/v1/knowledge-bases", headers=headers, json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "knowledge_base_exists"
