from io import BytesIO

from fastapi.testclient import TestClient

from tests.conftest import auth_headers
from tests.test_documents import create_knowledge_base, wait_for_job


def prepare_knowledge(client: TestClient, headers: dict[str, str]) -> str:
    knowledge_base_id = create_knowledge_base(client, headers)
    upload = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"knowledge_base_id": knowledge_base_id, "chunk_size": "300", "chunk_overlap": "30"},
        files={
            "file": (
                "xiaomi14.md",
                BytesIO("# 小米 14 充电\n小米 14 支持 90W 有线快充，电池容量 4610mAh。".encode()),
                "text/markdown",
            )
        },
    ).json()
    job = wait_for_job(client, headers, upload["job_id"])
    assert job["status"] == "succeeded"
    return knowledge_base_id


def test_grounded_chat_returns_actual_source_and_history(
    client: TestClient, users: dict[str, str]
) -> None:
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_knowledge(client, operator_headers)
    user_headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "小米 14 的充电功率是多少？"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["fallback"] is False
    assert "90W" in body["answer"]
    assert body["sources"][0]["filename"] == "xiaomi14.md"
    assert "90W" in body["sources"][0]["snippet"]
    history = client.get(
        f"/api/v1/conversations/{body['conversation_id']}", headers=user_headers
    ).json()
    assert [item["role"] for item in history["messages"]] == ["user", "assistant"]


def test_unrelated_question_falls_back_without_sources(
    client: TestClient, users: dict[str, str]
) -> None:
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_knowledge(client, operator_headers)
    user_headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "火星上的天气怎么样？"},
    )

    assert response.status_code == 200
    assert response.json()["fallback"] is True
    assert response.json()["sources"] == []
    assert "未找到可靠依据" in response.json()["answer"]


def test_feedback_is_idempotently_updated(client: TestClient, users: dict[str, str]) -> None:
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_knowledge(client, operator_headers)
    user_headers = auth_headers(client, "customer", users["customer"])
    chat = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "小米 14 电池容量？"},
    ).json()

    first = client.post(
        "/api/v1/chat/feedback",
        headers=user_headers,
        json={"message_id": chat["message_id"], "rating": "up"},
    )
    second = client.post(
        "/api/v1/chat/feedback",
        headers=user_headers,
        json={"message_id": chat["message_id"], "rating": "down", "correction": "需核对"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["rating"] == "down"


def test_streaming_chat_emits_contract_events(client: TestClient, users: dict[str, str]) -> None:
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_knowledge(client, operator_headers)
    user_headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "小米 14 充电？", "stream": True},
    )

    assert response.status_code == 200
    text = response.text
    assert "event: meta" in text
    assert "event: delta" in text
    assert "event: sources" in text
    assert "event: done" in text
    assert text.index("event: meta") < text.index("event: delta") < text.index("event: sources")


def test_follow_up_rewrite_keeps_product_context(client: TestClient, users: dict[str, str]) -> None:
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_knowledge(client, operator_headers)
    user_headers = auth_headers(client, "customer", users["customer"])
    first = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "小米 14 怎么样？"},
    ).json()

    follow_up = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={
            "knowledge_base_id": knowledge_base_id,
            "conversation_id": first["conversation_id"],
            "message": "它的充电功率是多少？",
        },
    )

    assert follow_up.status_code == 200
    assert follow_up.json()["fallback"] is False
    assert "90W" in follow_up.json()["answer"]


def test_explicit_human_transfer_is_suggested_immediately(
    client: TestClient, users: dict[str, str]
) -> None:
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_knowledge(client, operator_headers)
    user_headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "请转人工客服"},
    )

    assert response.status_code == 200
    assert response.json()["transfer_suggested"] is True
    assert response.json()["fallback"] is False


def test_sensitive_credentials_are_blocked_and_audited(
    client: TestClient, users: dict[str, str]
) -> None:
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_knowledge(client, operator_headers)
    user_headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "我的支付密码是 123456"},
    )
    audit = client.get("/api/v1/operations/audit", headers=operator_headers)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "sensitive_input"
    assert audit.status_code == 200
    assert audit.json()[0]["event_type"] == "audit:blocked_input"
    assert "123456" not in str(audit.json()[0]["payload"])
