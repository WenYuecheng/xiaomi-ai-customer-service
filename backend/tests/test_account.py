from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import User, UserRole


def test_register_creates_normalized_user_and_returns_authenticated_session(
    client: TestClient,
    application,
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "  New_User  ",
            "password": "SecurePass123",
            "password_confirm": "SecurePass123",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["access_token"]
    assert body["user"]["username"] == "new_user"
    assert body["user"]["display_name"] == "new_user"
    assert body["user"]["avatar_key"] == "aurora"
    assert body["user"]["role"] == "user"
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    with application.state.session_factory() as session:
        user = session.scalar(select(User).where(User.username == "new_user"))
        assert user is not None
        assert user.role == UserRole.user


def test_register_rejects_weak_password_mismatch_and_role_escalation(client: TestClient) -> None:
    weak = client.post(
        "/api/v1/auth/register",
        json={"username": "weak_user", "password": "password", "password_confirm": "password"},
    )
    mismatch = client.post(
        "/api/v1/auth/register",
        json={"username": "match_user", "password": "Password123", "password_confirm": "Other123"},
    )
    escalation = client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin_user",
            "password": "Password123",
            "password_confirm": "Password123",
            "role": "admin",
        },
    )

    assert weak.status_code == 422
    assert mismatch.status_code == 422
    assert escalation.status_code == 422
    assert all(
        item.json()["error"]["code"] == "validation_error"
        for item in (weak, mismatch, escalation)
    )


def test_register_rejects_duplicate_username_and_rate_limits_source(client: TestClient) -> None:
    payload = {
        "username": "limited_user",
        "password": "Password123",
        "password_confirm": "Password123",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201

    for _ in range(4):
        duplicate = client.post("/api/v1/auth/register", json=payload)
        assert duplicate.status_code == 409
        assert duplicate.json()["error"]["code"] == "user_exists"

    limited = client.post("/api/v1/auth/register", json=payload)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "registration_rate_limited"
    assert int(limited.headers["Retry-After"]) > 0
