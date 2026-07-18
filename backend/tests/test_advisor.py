from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.rag.providers import (
    AdvisorCandidateDraft,
    AdvisorPlanDraft,
    AdvisorRecommendationDraft,
    LangChainChatProvider,
)
from tests.conftest import auth_headers
from tests.test_documents import create_knowledge_base, wait_for_job


def prepare_advisor_knowledge(client: TestClient, headers: dict[str, str]) -> str:
    knowledge_base_id = create_knowledge_base(client, headers)
    content = """category: 手机
product_models: 小米 14|REDMI K80
# 手机选购资料
小米 14 配备 4610mAh 电池，支持 90W 有线快充，屏幕尺寸为 6.36 英寸。
REDMI K80 配备 6550mAh 电池，支持 90W 有线快充，采用 2K 屏幕。
"""
    upload = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"knowledge_base_id": knowledge_base_id, "chunk_size": "300", "chunk_overlap": "30"},
        files={"file": ("phone-advisor.md", BytesIO(content.encode()), "text/markdown")},
    ).json()
    assert wait_for_job(client, headers, upload["job_id"])["status"] == "succeeded"
    return knowledge_base_id


def test_advisor_plan_rejects_sources_outside_candidate_whitelist() -> None:
    plan = AdvisorPlanDraft(
        title="手机选购方案",
        interpreted_need="重视续航",
        candidates=[
            AdvisorCandidateDraft(
                model="小米 14",
                fit_score=88,
                highlights=["充电速度快"],
                tradeoffs=["资料未提供价格"],
                dimension_scores={"battery": 80},
                source_chunk_ids=["invented"],
            )
        ],
        comparison_rows=[],
        recommendation=AdvisorRecommendationDraft(
            primary_model="小米 14", summary="适合均衡需求", reasons=["配置均衡"], caveats=[]
        ),
        follow_up_suggestions=["更重视续航时怎么选？"],
    )

    class StructuredModel:
        def with_structured_output(self, schema, *, method: str):
            assert schema is AdvisorPlanDraft
            assert method == "json_mode"

            class Invoker:
                def invoke(self, messages):
                    return plan

            return Invoker()

    with pytest.raises(ValueError, match="candidate whitelist"):
        LangChainChatProvider(StructuredModel()).generate_advisor(
            "推荐手机",
            [{"chunk_id": "real", "snippet": "小米 14 电池容量 4610mAh"}],
        )


def test_advisor_session_is_saved_followed_up_and_user_isolated(
    client: TestClient, users: dict[str, str]
) -> None:
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_advisor_knowledge(client, operator_headers)
    customer_headers = auth_headers(client, "customer", users["customer"])

    created = client.post(
        "/api/v1/advisor/sessions",
        headers=customer_headers,
        json={
            "knowledge_base_id": knowledge_base_id,
            "message": "小米 14 和 REDMI K80 怎么选？我更重视续航",
            "mode": "comparison",
            "category": "phone",
            "product_models": ["小米 14", "REDMI K80"],
            "priorities": ["battery", "screen"],
        },
    )

    assert created.status_code == 200, created.text
    body = created.json()
    assert body["session"]["category"] == "phone"
    assert body["turn"]["plan"]["candidates"]
    assert [step["stage"] for step in body["turn"]["ai_trace"]] == [
        "understanding",
        "retrieval",
        "reranking",
        "generation",
        "grounding",
    ]
    assert all(source["chunk_id"] for source in body["turn"]["sources"])

    follow_up = client.post(
        f"/api/v1/advisor/sessions/{body['session']['id']}/turns",
        headers=customer_headers,
        json={"message": "如果更看重便携性呢？"},
    )
    assert follow_up.status_code == 200, follow_up.text
    assert follow_up.json()["sequence_no"] == 2

    other_headers = auth_headers(client, "admin", users["admin"])
    assert (
        client.get(
            f"/api/v1/advisor/sessions/{body['session']['id']}", headers=other_headers
        ).status_code
        == 404
    )

    listing = client.get("/api/v1/advisor/sessions", headers=customer_headers)
    assert listing.status_code == 200
    assert listing.json()["items"][0]["turn_count"] == 2

    deleted = client.delete(
        f"/api/v1/advisor/sessions/{body['session']['id']}", headers=customer_headers
    )
    assert deleted.status_code == 204


def test_advisor_stream_emits_trace_plan_sources_and_done(
    client: TestClient, users: dict[str, str]
) -> None:
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_advisor_knowledge(client, operator_headers)
    customer_headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/advisor/sessions",
        headers=customer_headers,
        json={
            "knowledge_base_id": knowledge_base_id,
            "message": "推荐一款续航好的手机",
            "category": "phone",
            "priorities": ["battery"],
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert response.text.index("event: meta") < response.text.index("event: trace")
    assert response.text.index("event: trace") < response.text.index("event: advisor")
    assert response.text.index("event: advisor") < response.text.index("event: sources")
    assert response.text.index("event: sources") < response.text.index("event: done")


def test_sensitive_advisor_input_is_blocked_before_any_model_call(
    client: TestClient, users: dict[str, str], monkeypatch
) -> None:
    calls = 0

    def forbidden_provider(_settings):
        nonlocal calls
        calls += 1
        raise AssertionError("provider must not be created")

    monkeypatch.setattr("app.advisor.service.create_chat_provider", forbidden_provider)
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = create_knowledge_base(client, operator_headers)
    customer_headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/advisor/sessions",
        headers=customer_headers,
        json={
            "knowledge_base_id": knowledge_base_id,
            "message": "我的支付密码是 TEST-123456，请推荐手机",
            "category": "phone",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "sensitive_input"
    assert calls == 0
