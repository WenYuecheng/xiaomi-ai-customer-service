from io import BytesIO

from fastapi.testclient import TestClient

from app.rag.providers import QuestionAnalysis, RerankDecision, RerankResult
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


def test_source_includes_original_public_url(client: TestClient, users: dict[str, str]) -> None:
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
    class CountingProvider:
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
    class RejectingProvider:
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
    class FailingRerankProvider:
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
    client: TestClient, users: dict[str, str], monkeypatch
) -> None:
    class TransferProvider:
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
