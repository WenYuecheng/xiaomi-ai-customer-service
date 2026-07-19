"""
文件职责：
该文件负责测试智能导购顾问（Advisor）相关的功能，包括方案生成、会话隔离、流式输出、敏感拦截与内容落地。

所属功能：
智能导购/顾问会话模块

主要流程：
提供测试用的知识库初始化函数，再通过一系列隔离的测试用例来验证导购生命周期中的各项核心逻辑。
"""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.rag.providers import (
    AdvisorCandidateDraft,
    AdvisorPlanDraft,
    AdvisorRecommendationDraft,
    LangChainChatProvider,
)
from app.rag.retrieval import RetrievedSource
from tests.conftest import auth_headers
from tests.test_documents import create_knowledge_base, wait_for_job


def prepare_advisor_knowledge(client: TestClient, headers: dict[str, str]) -> str:
    """
    准备导购测试所需的测试知识库，并上传一篇 Markdown 格式的手机测试数据。

    Args:
        client: 用于发起请求的 TestClient。
        headers: 鉴权相关的请求头信息。

    Returns:
        str: 生成的 knowledge_base_id，用于后续发起相关会话。

    Raises:
        AssertionError: 当上传文档的处理任务没有成功完成时。
    """
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
    """
    测试导购方案的来源白名单机制：当模型返回的来源块 ID 不在提供给模型的上下文块 ID 白名单内时，
    服务应该抛出 ValueError 拒绝接受，以避免模型“幻觉”捏造来源。
    """
    # 构造一个包含非法来源（invented）的伪造方案
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

    messages_seen: list[dict[str, str]] = []

    class StructuredModel:
        """
        用于模拟 LangChain 模型对象的 Mock 类，主要用于验证向模型传递的 prompt 或输出结构。
        """

        def with_structured_output(self, schema, *, method: str):
            # 确认传入的要求结构是预期的 AdvisorPlanDraft
            assert schema is AdvisorPlanDraft
            assert method == "json_mode"

            class Invoker:
                def invoke(self, messages):
                    # 记录并保存发送给模型的 messages，用于后续验证
                    messages_seen.extend(messages)
                    # 返回之前伪造的、包含非法 source_chunk_ids 的 plan
                    return plan

            return Invoker()

    with pytest.raises(ValueError, match="candidate whitelist"):
        LangChainChatProvider(StructuredModel()).generate_advisor(
            "推荐手机",
            [{"chunk_id": "real", "snippet": "小米 14 电池容量 4610mAh"}],
        )
    assert '"source_chunk_ids"' in messages_seen[0]["content"]
    assert '"dimension_scores"' in messages_seen[0]["content"]


def test_advisor_session_is_saved_followed_up_and_user_isolated(
    client: TestClient, users: dict[str, str]
) -> None:
    """
    测试顾问会话的核心生命周期：
    1. 正常创建并保存新会话。
    2. 能正确地在同一个会话下发起追问。
    3. 确保跨用户隔离，管理员或非所有者不能查看他人的会话。
    4. 可以查询会话列表，并确保追问能够累积会话轮数。
    5. 用户可以正常删除自己的会话。
    """
    operator_headers = auth_headers(client, "operator", users["operator"])
    # 预设管理员上传测试数据
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
    """
    测试导购的流式响应（SSE），确保能够按照预期的事件顺序下发各个阶段的事件数据。
    预期的事件流顺序为：meta -> trace -> advisor -> sources -> done。
    """
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
    """
    测试敏感信息拦截机制：
    当用户输入包含如密码等敏感词时，应在进入底层 LLM 服务之前被直接拦截，
    返回 400 错误码和 sensitive_input 错误标识。
    """
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


def test_advisor_retrieval_guarantees_a_query_for_each_requested_model(monkeypatch) -> None:
    """
    测试顾问的多商品检索策略：
    当用户询问涉及多个产品型号时，检索阶段应为整个请求以及每个特定型号分别发起检索，
    保证关于每个产品的资料都能被尽可能检索到。
    """
    from app.advisor.service import retrieve_advisor_sources

    calls: list[str] = []

    def fake_retrieve(_db, _vector_store, _knowledge_base_id, query, **_kwargs):
        calls.append(query)
        if query == "小米 14":
            return [RetrievedSource("d1", "c1", "xiaomi14.md", "全文", "小米 14 资料", 0.8)]
        if query == "REDMI K80":
            return [RetrievedSource("d2", "c2", "k80.md", "全文", "REDMI K80 资料", 0.9)]
        return [RetrievedSource("d1", "c1", "xiaomi14.md", "全文", "小米 14 资料", 0.7)]

    monkeypatch.setattr("app.advisor.service.retrieve_sources", fake_retrieve)
    sources = retrieve_advisor_sources(
        object(),
        object(),
        "kb-1",
        "小米 14 和 REDMI K80 怎么选",
        ["小米 14", "REDMI K80"],
        threshold=0.25,
        require_lexical_overlap=False,
    )

    assert calls == ["小米 14 和 REDMI K80 怎么选", "小米 14", "REDMI K80"]
    assert [source.chunk_id for source in sources] == ["c2", "c1"]


def test_advisor_grounding_removes_unsupported_numbers_from_recommendation() -> None:
    """
    测试内容落地与对齐（Grounding）策略：
    当模型生成的推荐结论中包含源数据中并不存在的数据（如捏造了 '42%' 这个数字）时，
    Grounding 服务应将其判定为不受支持，并将其替换为“资料未明确”。
    """
    from app.advisor.service import ground_plan

    plan = {
        "candidates": [
            {
                "model": "REDMI K80",
                "highlights": ["电池容量 6550mAh"],
                "tradeoffs": [],
                "source_chunk_ids": ["k80"],
            }
        ],
        "comparison_rows": [],
        "recommendation": {
            "primary_model": "REDMI K80",
            "summary": "电池容量为 6550mAh，续航配置更突出",
            "reasons": ["相比另一候选，电池容量高出 42%"],
            "caveats": ["实际续航需结合使用场景"],
        },
        "follow_up_suggestions": ["是否还需要对比 120W 充电？"],
    }
    sources = [{"chunk_id": "k80", "snippet": "REDMI K80 配备 6550mAh 电池"}]

    grounded = ground_plan(plan, sources)

    assert grounded["recommendation"]["summary"] == "电池容量为 6550mAh，续航配置更突出"
    assert grounded["recommendation"]["reasons"] == ["资料未明确"]
    assert grounded["recommendation"]["caveats"] == ["实际续航需结合使用场景"]
    assert grounded["follow_up_suggestions"] == ["资料未明确"]
