"""
文件职责：
该文件负责测试账户相关的 API 功能，包括用户注册、资料更新、密码修改以及个人主页仪表盘数据的获取。

所属功能：
用户认证与账户管理 (User Authentication & Account Management)

主要流程：
1. 测试正常用户注册流程。
2. 测试注册时的边界条件与异常处理。
3. 测试用户修改显示名称和头像。
4. 测试密码修改及安全机制。
5. 测试个人主页数据的聚合和权限隔离。
"""

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
    """
    测试正常提交注册信息后，可以建立经过正常化处理（如去除两端空格、转小写等）的用户，
    并直接返回可以用于校验身份的授权 Token。

    Args:
        client: 测试客户端。
        application: ASGI 应用对象，用于取得后台 session_factory 查询验证。

    Returns:
        None

    Raises:
        AssertionError: 响应不是 201 注册成功，或存储到 DB 中的对象信息有误。
    """
    # 提交带有不规则空格和大写的 username 请求
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
    """
    测试各种由于安全条件不足和恶意提权的无效注册会被系统拒绝。

    Args:
        client: 测试客户端。

    Returns:
        None

    Raises:
        AssertionError: 如果系统通过了这些包含不合规参数的请求（未返回 422 校验错）。
    """
    # 模拟弱密码注册请求
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
        item.json()["error"]["code"] == "validation_error" for item in (weak, mismatch, escalation)
    )


def test_register_rejects_duplicate_username_and_rate_limits_source(client: TestClient) -> None:
    """
    测试相同的用户名再次注册会被拒绝，并且同一来源过快的重复请求会触发频控拦截。

    Args:
        client: 测试客户端。

    Returns:
        None

    Raises:
        AssertionError: 重复注册未返回 409，或短时间高频请求未返回 429。
    """
    # 预设一条标准注册负载并产生第一条记录
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
    """
    测试用户资料编辑接口允许修改显示名并且仅允许使用系统预设的合法头像键值。

    Args:
        client: 测试客户端。
        users: 预置用户字典。

    Returns:
        None

    Raises:
        AssertionError: 正常更新未返回 200，或者异常更新未遭到校验拦截。
    """
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
    """
    测试修改密码后旧的 Token 会失效，且由于安全合规原因，审计记录中不能包含密码等敏感信息。

    Args:
        client: 测试客户端。
        application: 应用对象。
        users: 预置用户字典。

    Returns:
        None

    Raises:
        AssertionError: 改密流程被异常阻断、旧 Token 仍能访问，或审计信息内含敏感密码。
    """
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
    """
    测试账户主页和活动游标分页接口可以返回正确编排好的数据，同时必须满足多租户间数据不发生越权。
    需要构造复杂的历史聊天、顾问会话、评价反馈等信息以进行验证。

    Args:
        client: 测试客户端。
        application: 应用对象。
        users: 预置用户字典。

    Returns:
        None

    Raises:
        AssertionError: 最终主页各项统计数值不符合预设入库条件，或活动列表条目缺失/排序有误。
    """
    now = datetime.now(UTC)
    with application.state.session_factory() as session:
        # 获取系统内的普通顾客及操作员以分配属主
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

    # 使用该顾客身份访问包含刚刚插入数据的仪表盘和活动轨迹
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
