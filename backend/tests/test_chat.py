"""
文件职责：
该文件负责测试基于知识库的问答聊天（Chat）核心逻辑，包括普通问答、基于知识源的验证、检索、流式返回、人工转接及边界异常处理。

所属功能：
智能问答会话模块

主要流程：
提供知识库准备函数，然后通过一系列独立的单元测试验证聊天接口的不同场景。
"""

from io import BytesIO

from fastapi.testclient import TestClient

from app.rag.providers import QuestionAnalysis, RerankDecision, RerankResult
from tests.conftest import auth_headers
from tests.test_documents import create_knowledge_base, wait_for_job


def prepare_knowledge(client: TestClient, headers: dict[str, str]) -> str:
    """
    准备测试用知识库，并上传测试 Markdown 文档用于问答。

    Args:
        client: 用于发起请求的 TestClient。
        headers: 鉴权相关的请求头信息。

    Returns:
        str: 知识库的 knowledge_base_id。

    Raises:
        AssertionError: 上传任务未成功时抛出异常。
    """
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
    """
    测试带事实根据的问答：
    1. 确保在回答正确的同时，能够正确返回原始的来源依据内容（如文档名称和片段）。
    2. 验证各个 AI 处理阶段（理解、检索、重排、生成、对齐）是否都被成功记录。
    3. 验证历史记录是否能够正确被持久化和查询。
    """
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
    assert [step["stage"] for step in body["ai_trace"]] == [
        "understanding",
        "retrieval",
        "reranking",
        "generation",
        "grounding",
    ]
    assert body["ai_trace"][0]["status"] == "completed"
    assert body["ai_trace"][2]["status"] == "completed"
    assert body["ai_trace"][2]["details"]
    assert body["ai_trace"][3]["status"] == "completed"
    history = client.get(
        f"/api/v1/conversations/{body['conversation_id']}", headers=user_headers
    ).json()
    assert [item["role"] for item in history["messages"]] == ["user", "assistant"]
    assert history["messages"][1]["ai_trace"] == body["ai_trace"]


def test_product_comparison_returns_saved_structured_advisor_plan(
    client: TestClient, users: dict[str, str]
) -> None:
    """
    测试产品对比功能在问答接口中的触发：
    当用户在普通聊天接口提出带有“对比”、“判断”等导购意图的问题时，
    应返回导购生成的结构化方案，并生成 advisor_session_id 关联。
    """
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_knowledge(client, operator_headers)
    user_headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={
            "knowledge_base_id": knowledge_base_id,
            "message": "对比一下小米 14，帮我判断是否适合重视续航的人",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["advisor_plan"]["candidates"]
    assert body["advisor_session_id"]
    history = client.get(
        f"/api/v1/conversations/{body['conversation_id']}", headers=user_headers
    ).json()
    assert history["messages"][-1]["advisor_plan"] == body["advisor_plan"]


def test_source_includes_original_public_url(client: TestClient, users: dict[str, str]) -> None:
    """
    测试数据来源的外部 URL 携带功能：
    如果在上传文档时提供了 source_url，那么最终回答附带的知识来源中也必须包含该外部 URL。
    """
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = create_knowledge_base(client, operator_headers)
    upload = client.post(
        "/api/v1/documents/upload",
        headers=operator_headers,
        data={
            "knowledge_base_id": knowledge_base_id,
            "source_url": "https://www.mi.com/example",
        },
        files={
            "file": (
                "source.md",
                BytesIO("小米 14 支持 90W 有线快充。".encode()),
                "text/markdown",
            )
        },
    ).json()
    wait_for_job(client, operator_headers, upload["job_id"])
    user_headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "小米 14 支持多少瓦快充？"},
    )

    assert response.status_code == 200
    assert response.json()["sources"][0]["source_url"] == "https://www.mi.com/example"


def test_unrelated_question_falls_back_without_sources(
    client: TestClient, users: dict[str, str]
) -> None:
    """
    测试知识库拒答与 Fallback 机制：
    当用户问与知识库完全无关的问题（如“火星天气”）时，系统应判断为无法根据知识库回答，
    触发 fallback 并跳过最终的文本生成步骤。
    """
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
    generation = next(step for step in response.json()["ai_trace"] if step["stage"] == "generation")
    assert generation["status"] == "skipped"
    assert "没有可靠依据" in generation["summary"]


def test_model_is_called_three_times_only_when_reliable_sources_exist(
    client: TestClient, users: dict[str, str], monkeypatch
) -> None:
    """
    测试正常回答路径的模型调用次数：
    1. 通过分析意图（Analyze）、重排序（Rerank）到最终生成（Generate）。
    2. 当 Fallback 时，只调用分析意图与重排序，不调用最终生成以节省 Token。
    """

    class CountingProvider:
        """用于统计 LLM 调用次数的 Mock Provider"""

        analysis_calls = 0
        rerank_calls = 0
        generation_calls = 0

        def analyze(self, question, summary=None, recent_messages=None):
            del summary, recent_messages
            self.analysis_calls += 1
            return QuestionAnalysis(
                intent="knowledge_query",
                rewritten_question=question,
                product_models=["小米 14"] if "小米" in question else [],
                need_retrieval=True,
                confidence=0.99,
            )

        def rerank(self, question, candidates, top_k):
            del question
            self.rerank_calls += 1
            return RerankResult(
                decisions=[
                    RerankDecision(
                        chunk_id=item.chunk_id,
                        relevance_score=1,
                        reason="直接包含答案",
                    )
                    for item in candidates[:top_k]
                ]
            )

        def generate(self, question, contexts, summary=None, recent_messages=None):
            del question, summary, recent_messages
            self.generation_calls += 1
            return f"根据知识库，{contexts[0]}"

        def stream(self, question, contexts, summary=None, recent_messages=None):
            yield self.generate(question, contexts, summary, recent_messages)

    provider = CountingProvider()
    monkeypatch.setattr("app.chat.service.create_chat_provider", lambda _settings: provider)
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_knowledge(client, operator_headers)
    user_headers = auth_headers(client, "customer", users["customer"])

    grounded = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "小米 14 充电功率？"},
    )
    fallback = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "火星天气？"},
    )

    assert grounded.status_code == 200
    assert fallback.status_code == 200
    assert provider.analysis_calls == 2
    assert provider.rerank_calls == 1
    assert provider.generation_calls == 1


def test_reranker_can_reject_all_candidates_without_calling_generation(
    client: TestClient, users: dict[str, str], monkeypatch
) -> None:
    """
    测试重排序（Reranker）全部拒绝的情况：
    如果 Reranker 认为所有检索候选均不相关，系统应跳过最终生成步骤，
    直接降级返回并标记失败原因。
    """

    class RejectingProvider:
        """一个始终返回空重排决策结果的 Mock Provider，从而模拟全部候选内容都被拒绝"""

        analysis_calls = 0
        rerank_calls = 0
        generation_calls = 0

        def analyze(self, question, summary=None, recent_messages=None):
            del summary, recent_messages
            self.analysis_calls += 1
            return QuestionAnalysis(
                intent="knowledge_query",
                rewritten_question=question,
                product_models=["小米 14"],
                need_retrieval=True,
                confidence=1,
            )

        def rerank(self, question, candidates, top_k):
            del question, candidates, top_k
            self.rerank_calls += 1
            return RerankResult(decisions=[])

        def generate(self, question, contexts, summary=None, recent_messages=None):
            del question, contexts, summary, recent_messages
            self.generation_calls += 1
            return "不应调用"

        def stream(self, question, contexts, summary=None, recent_messages=None):
            yield self.generate(question, contexts, summary, recent_messages)

    provider = RejectingProvider()
    monkeypatch.setattr("app.chat.service.create_chat_provider", lambda _settings: provider)
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_knowledge(client, operator_headers)
    user_headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "小米 14 充电功率？"},
    )

    assert response.status_code == 200
    assert response.json()["fallback"] is True
    assert response.json()["sources"] == []
    assert provider.analysis_calls == 1
    assert provider.rerank_calls == 1
    assert provider.generation_calls == 0
    reranking = next(step for step in response.json()["ai_trace"] if step["stage"] == "reranking")
    assert reranking["status"] == "completed"
    assert "未保留" in reranking["summary"]


def test_reranker_failure_degrades_to_vector_order_and_still_generates(
    client: TestClient, users: dict[str, str], monkeypatch
) -> None:
    """
    测试 Reranker 故障降级机制：
    当 Reranker 模型或解析抛出异常时，为了高可用性，不应直接报错中断，
    而应降级使用底层向量检索的初始顺序继续生成回答。
    """

    class FailingRerankProvider:
        """一个模拟在 Rerank 阶段抛出异常的 Mock Provider"""

        analysis_calls = 0
        rerank_calls = 0
        generation_calls = 0

        def analyze(self, question, summary=None, recent_messages=None):
            del summary, recent_messages
            self.analysis_calls += 1
            return QuestionAnalysis(
                intent="knowledge_query",
                rewritten_question=question,
                product_models=["小米 14"],
                need_retrieval=True,
                confidence=1,
            )

        def rerank(self, question, candidates, top_k):
            del question, candidates, top_k
            self.rerank_calls += 1
            raise ValueError("invalid structured rerank result")

        def generate(self, question, contexts, summary=None, recent_messages=None):
            del question, summary, recent_messages
            self.generation_calls += 1
            return f"降级后仍依据知识回答：{contexts[0]}"

        def stream(self, question, contexts, summary=None, recent_messages=None):
            yield self.generate(question, contexts, summary, recent_messages)

    provider = FailingRerankProvider()
    monkeypatch.setattr("app.chat.service.create_chat_provider", lambda _settings: provider)
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_knowledge(client, operator_headers)
    user_headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "小米 14 充电功率？"},
    )

    assert response.status_code == 200
    assert response.json()["fallback"] is False
    assert response.json()["sources"]
    assert provider.analysis_calls == 1
    assert provider.rerank_calls == 1
    assert provider.generation_calls == 1
    reranking = next(step for step in response.json()["ai_trace"] if step["stage"] == "reranking")
    assert reranking["status"] == "degraded"
    assert "原始排序" in reranking["summary"]


def test_feedback_is_idempotently_updated(client: TestClient, users: dict[str, str]) -> None:
    """
    测试用户反馈（点赞/点踩）的幂等与更新机制：
    同一个消息的重复反馈应执行覆盖更新操作，而不是重复插入。
    """
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
    """
    测试流式问答输出契约：
    确保 SSE 事件不仅包含答案块（delta），还严格按照预期顺序输出
    meta、trace、sources 和 done 等关键事件。
    """
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
    assert "event: trace" in text
    assert text.index("event: meta") < text.index("event: trace") < text.index("event: delta")
    assert text.index("event: delta") < text.index("event: sources") < text.index("event: done")
    assert '"stage":"understanding"' in text
    assert '"stage":"reranking"' in text
    assert '"stage":"grounding"' in text
    events = []
    for block in text.split("\n\n"):
        event = next((line[7:] for line in block.splitlines() if line.startswith("event: ")), None)
        data = next((line[6:] for line in block.splitlines() if line.startswith("data: ")), None)
        if event and data:
            import json

            payload = json.loads(data)
            events.append((event, payload.get("stage"), payload.get("status")))
    assert events[:8] == [
        ("meta", None, None),
        ("trace", "understanding", "running"),
        ("trace", "understanding", "completed"),
        ("trace", "retrieval", "running"),
        ("trace", "retrieval", "completed"),
        ("trace", "reranking", "running"),
        ("trace", "reranking", "completed"),
        ("trace", "generation", "running"),
    ]


def test_streaming_fallback_emits_each_terminal_trace_once(
    client: TestClient, users: dict[str, str]
) -> None:
    """
    测试流式 Fallback 状态下的追踪事件输出：
    确保触发拒答时，各关键阶段状态（例如 generation 的 skipped 状态）
    都能正确且唯一地通过流输出。
    """
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_knowledge(client, operator_headers)
    user_headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=user_headers,
        json={
            "knowledge_base_id": knowledge_base_id,
            "message": "火星天气？",
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert response.text.count('"stage":"generation","status":"skipped"') == 1
    assert response.text.count('"stage":"grounding","status":"completed"') == 1


def test_follow_up_rewrite_keeps_product_context(client: TestClient, users: dict[str, str]) -> None:
    """
    测试多轮对话重写：
    验证追问（如代词“它”）是否能正确结合历史对话上下文重写并检索出产品信息。
    """
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
    client: TestClient, users: dict[str, str], monkeypatch
) -> None:
    """
    测试人工客服转接检测：
    当问题明确属于人工转接意图时，跳过复杂的检索生成逻辑，
    直接返回转接建议标识（transfer_suggested = True）。
    """

    class TransferProvider:
        """模拟分析判定结果为需要人工转接的 Mock Provider"""

        analysis_calls = 0
        rerank_calls = 0
        generation_calls = 0

        def analyze(self, question, summary=None, recent_messages=None):
            del summary, recent_messages
            self.analysis_calls += 1
            return QuestionAnalysis(
                intent="human_transfer",
                rewritten_question=question,
                product_models=[],
                need_retrieval=False,
                confidence=1,
            )

        def rerank(self, question, candidates, top_k):
            del question, candidates, top_k
            self.rerank_calls += 1
            return RerankResult(decisions=[])

        def generate(self, question, contexts, summary=None, recent_messages=None):
            del question, contexts, summary, recent_messages
            self.generation_calls += 1
            return "不应调用"

        def stream(self, question, contexts, summary=None, recent_messages=None):
            yield self.generate(question, contexts, summary, recent_messages)

    provider = TransferProvider()
    monkeypatch.setattr("app.chat.service.create_chat_provider", lambda _settings: provider)
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
    assert provider.analysis_calls == 1
    assert provider.rerank_calls == 0
    assert provider.generation_calls == 0


def test_sensitive_credentials_are_blocked_and_audited(
    client: TestClient, users: dict[str, str], monkeypatch
) -> None:
    """
    测试聊天接口的敏感数据脱敏与审计记录：
    确保类似密码等敏感信息被请求阻拦，且在审计日志中原始明文信息已被脱敏掩码（MASK）处理，保护用户隐私。
    """
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = prepare_knowledge(client, operator_headers)
    user_headers = auth_headers(client, "customer", users["customer"])
    monkeypatch.setattr(
        "app.chat.service.create_chat_provider",
        lambda _settings: (_ for _ in ()).throw(AssertionError("敏感输入不得进入模型")),
    )

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
