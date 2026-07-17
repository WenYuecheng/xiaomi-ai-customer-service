from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_login_and_me_return_verified_user(client: TestClient, users: dict[str, str]) -> None:
    headers = auth_headers(client, "admin", users["admin"])

    response = client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["username"] == "admin"
    assert response.json()["role"] == "admin"
    assert "password_hash" not in response.json()


def test_invalid_password_is_rejected(client: TestClient, users: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_operator_can_create_and_filter_knowledge_bases(
    client: TestClient, users: dict[str, str]
) -> None:
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
    headers = auth_headers(client, "operator", users["operator"])
    payload = {"name": "重复名称"}
    assert client.post("/api/v1/knowledge-bases", headers=headers, json=payload).status_code == 201

    response = client.post("/api/v1/knowledge-bases", headers=headers, json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "knowledge_base_exists"

