from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import (
    AdvisorSession,
    AdvisorTurn,
    BehaviorEvent,
    Conversation,
    Feedback,
    FeedbackRating,
    KnowledgeBase,
    Message,
    MessageRole,
    User,
    UserRole,
)
from tests.conftest import auth_headers


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


def test_user_can_update_display_name_and_whitelisted_avatar(
    client: TestClient,
    users: dict[str, str],
) -> None:
    headers = auth_headers(client, "customer", users["customer"])

    updated = client.patch(
        "/api/v1/account/profile",
        headers=headers,
        json={"display_name": "  小米探索者  ", "avatar_key": "cosmos"},
    )
    invalid_avatar = client.patch(
        "/api/v1/account/profile",
        headers=headers,
        json={"avatar_key": "../../avatar.png"},
    )

    assert updated.status_code == 200, updated.text
    assert updated.json()["display_name"] == "小米探索者"
    assert updated.json()["avatar_key"] == "cosmos"
    assert invalid_avatar.status_code == 422


def test_change_password_invalidates_old_tokens_and_never_audits_secrets(
    client: TestClient,
    application,
    users: dict[str, str],
) -> None:
    headers = auth_headers(client, "customer", users["customer"])
    wrong = client.post(
        "/api/v1/account/change-password",
        headers=headers,
        json={
            "current_password": "Wrong123",
            "new_password": "NewSecure123",
            "new_password_confirm": "NewSecure123",
        },
    )
    changed = client.post(
        "/api/v1/account/change-password",
        headers=headers,
        json={
            "current_password": users["customer"],
            "new_password": "NewSecure123",
            "new_password_confirm": "NewSecure123",
        },
    )

    assert wrong.status_code == 400
    assert wrong.json()["error"]["code"] == "invalid_current_password"
    assert changed.status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    new_headers = auth_headers(client, "customer", "NewSecure123")
    assert client.get("/api/v1/auth/me", headers=new_headers).status_code == 200
    with application.state.session_factory() as session:
        audit = session.scalar(
            select(BehaviorEvent).where(
                BehaviorEvent.event_type == "audit:account:password_changed"
            )
        )
        assert audit is not None
        assert "NewSecure123" not in str(audit.payload)
        assert users["customer"] not in str(audit.payload)


def test_account_dashboard_and_cursor_activity_are_grounded_and_user_isolated(
    client: TestClient,
    application,
    users: dict[str, str],
) -> None:
    now = datetime.now(UTC)
    with application.state.session_factory() as session:
        customer = session.scalar(select(User).where(User.username == "customer"))
        operator = session.scalar(select(User).where(User.username == "operator"))
        assert customer is not None and operator is not None
        knowledge_base = KnowledgeBase(
            name="个人主页测试库",
            description="dashboard test",
            owner_id=operator.id,
        )
        session.add(knowledge_base)
        session.flush()
        conversation = Conversation(
            user_id=customer.id,
            knowledge_base_id=knowledge_base.id,
            created_at=now - timedelta(days=3),
        )
        session.add(conversation)
        session.flush()
        question = Message(
            conversation_id=conversation.id,
            role=MessageRole.user,
            content="Xiaomi 14 的续航怎么样？",
            created_at=now - timedelta(days=3),
        )
        answer = Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content="依据资料，电池容量为 4610mAh。",
            created_at=now - timedelta(days=3, minutes=-1),
        )
        session.add_all([question, answer])
        session.flush()
        session.add(
            Feedback(
                message_id=answer.id,
                user_id=customer.id,
                rating=FeedbackRating.up,
                created_at=now - timedelta(days=1),
            )
        )
        advisor_session = AdvisorSession(
            user_id=customer.id,
            knowledge_base_id=knowledge_base.id,
            title="手机 AI 选购方案",
            category="phone",
        )
        session.add(advisor_session)
        session.flush()
        session.add(
            AdvisorTurn(
                session_id=advisor_session.id,
                sequence_no=1,
                question="小米 14 和 REDMI K80 怎么选？",
                requirements={},
                plan={"recommendation": {"summary": "续航优先可关注 REDMI K80"}},
                sources=[],
                ai_trace=[],
                status="completed",
                created_at=now - timedelta(days=2),
            )
        )
        session.add(
            BehaviorEvent(
                user_id=customer.id,
                event_type="chat",
                payload={"question": "Xiaomi 14 续航", "intent": "knowledge_query"},
                created_at=now - timedelta(days=3),
            )
        )
        session.commit()

    headers = auth_headers(client, "customer", users["customer"])
    dashboard = client.get("/api/v1/account/dashboard", headers=headers)
    first_page = client.get("/api/v1/account/activities?limit=2", headers=headers)

    assert dashboard.status_code == 200, dashboard.text
    body = dashboard.json()
    assert body["stats"]["consultation_count"] == 1
    assert body["stats"]["advisor_plan_count"] == 1
    assert body["stats"]["feedback_count"] == 1
    assert body["stats"]["helpful_rate"] == 100
    assert body["growth_level"] == 1
    assert body["interests"]["product_preferences"] == ["小米 14"]
    assert len(body["trend"]) == 14
    assert [item["type"] for item in body["recent_activities"]] == [
        "feedback",
        "advisor",
        "chat",
    ]
    assert first_page.status_code == 200
    assert len(first_page.json()["items"]) == 2
    assert first_page.json()["next_cursor"]
    second_page = client.get(
        "/api/v1/account/activities",
        headers=headers,
        params={"limit": 2, "cursor": first_page.json()["next_cursor"]},
    )
    assert [item["type"] for item in second_page.json()["items"]] == ["chat"]
    assert "payload" not in str(body)
