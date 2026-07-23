from io import BytesIO

from fastapi.testclient import TestClient

import app.chat.service as chat_service
from app.rag.providers import QuestionAnalysis
from tests.conftest import auth_headers
from tests.test_documents import wait_for_job


def create_library(client: TestClient, headers: dict[str, str], name: str) -> str:
    response = client.post("/api/v1/knowledge-bases", headers=headers, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def upload_markdown(
    client: TestClient,
    headers: dict[str, str],
    knowledge_base_id: str,
    filename: str,
    content: str,
) -> None:
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"knowledge_base_id": knowledge_base_id},
        files={"file": (filename, BytesIO(content.encode()), "text/markdown")},
    )
    assert response.status_code == 202, response.text
    assert wait_for_job(client, headers, response.json()["job_id"])["status"] == "succeeded"


def test_chat_searches_multiple_libraries_and_reports_source_library(
    client: TestClient, users: dict[str, str]
) -> None:
    operator = auth_headers(client, "operator", users["operator"])
    core_id = create_library(client, operator, "小米生态核心库-多库测试")
    official_id = create_library(client, operator, "小米中国官方完整知识库-多库测试")
    upload_markdown(
        client,
        operator,
        core_id,
        "xiaomi-17t.md",
        "# 小米 17T\n小米 17T 是手机，电池容量为 7000mAh。",
    )
    upload_markdown(
        client,
        operator,
        official_id,
        "robot-power.md",
        "# 扫地机器人无法开机\n电量不足时，请先靠上充电座充电后再使用。",
    )
    customer = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=customer,
        json={
            "knowledge_base_ids": [core_id, official_id],
            "message": "扫地机器人无法开机怎么排查？",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["knowledge_base_ids"] == [core_id, official_id]
    assert body["knowledge_base_id"] == core_id
    assert body["fallback"] is False
    assert any(source["knowledge_base_id"] == official_id for source in body["sources"])
    assert any(source["knowledge_base_name"] == "小米中国官方完整知识库-多库测试" for source in body["sources"])
    history = client.get(
        f"/api/v1/conversations/{body['conversation_id']}", headers=customer
    ).json()
    assert history["knowledge_base_ids"] == [core_id, official_id]


def test_chat_rejects_conflicting_legacy_and_multi_library_selection(
    client: TestClient, users: dict[str, str]
) -> None:
    operator = auth_headers(client, "operator", users["operator"])
    first_id = create_library(client, operator, "冲突库一")
    second_id = create_library(client, operator, "冲突库二")
    customer = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=customer,
        json={
            "knowledge_base_id": first_id,
            "knowledge_base_ids": [second_id],
            "message": "测试冲突",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "knowledge_base_selection_conflict"


def test_explicit_new_phone_model_overrides_incompatible_robot_history() -> None:
    apply_current_question_override = getattr(
        chat_service, "apply_current_question_override", None
    )
    assert apply_current_question_override is not None
    analysis = QuestionAnalysis(
        intent="troubleshooting",
        rewritten_question="小米17T扫地机器人无法开机怎么排查？",
        product_models=["小米17T"],
        need_retrieval=True,
        confidence=0.95,
    )

    guarded = apply_current_question_override("小米17T", analysis)

    assert guarded.intent == "knowledge_query"
    assert guarded.rewritten_question == "小米 17T 产品介绍"
    assert guarded.product_models == ["小米 17t"]
