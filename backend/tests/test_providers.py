from app.rag.providers import LangChainChatProvider, MockChatProvider, QuestionAnalysis


class RecordingModel:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def invoke(self, messages: list[dict[str, str]]):
        self.messages = messages
        return type("Response", (), {"content": "回答"})()

    def stream(self, messages: list[dict[str, str]]):
        self.messages = messages
        yield type("Chunk", (), {"content": "流"})()
        yield type("Chunk", (), {"content": "式"})()


class StructuredRecordingModel(RecordingModel):
    def __init__(self) -> None:
        super().__init__()
        self.structured_method: str | None = None

    def with_structured_output(self, schema, *, method: str):
        assert schema is QuestionAnalysis
        self.structured_method = method
        outer = self

        class StructuredInvoker:
            def invoke(self, messages):
                outer.messages = messages
                return QuestionAnalysis(
                    intent="knowledge_query",
                    rewritten_question="小米 14 支持多少瓦有线快充？",
                    product_models=["小米 14"],
                    need_retrieval=True,
                    confidence=0.98,
                )

        return StructuredInvoker()


def test_provider_sends_summary_and_recent_ten_turns_to_model() -> None:
    model = RecordingModel()
    provider = LangChainChatProvider(model)
    history = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": f"消息 {index}"}
        for index in range(24)
    ]

    result = provider.generate("当前问题", ["知识证据"], "旧会话摘要", history)

    assert result == "回答"
    assert "旧会话摘要" in model.messages[0]["content"]
    assert [message["content"] for message in model.messages[1:-1]] == [
        f"消息 {index}" for index in range(4, 24)
    ]
    assert model.messages[-1] == {"role": "user", "content": "当前问题"}


def test_provider_uses_native_model_stream() -> None:
    model = RecordingModel()
    provider = LangChainChatProvider(model)

    assert list(provider.stream("问题", ["证据"])) == ["流", "式"]


def test_provider_uses_json_mode_for_structured_question_analysis() -> None:
    model = StructuredRecordingModel()
    provider = LangChainChatProvider(model)

    result = provider.analyze(
        "它支持多少瓦快充？",
        "用户正在咨询小米 14",
        [{"role": "user", "content": "小米 14 怎么样？"}],
    )

    assert model.structured_method == "json_mode"
    assert result.intent == "knowledge_query"
    assert result.product_models == ["小米 14"]
    assert result.rewritten_question == "小米 14 支持多少瓦有线快充？"


def test_mock_provider_returns_deterministic_analysis() -> None:
    result = MockChatProvider().analyze(
        "它的充电功率是多少？",
        None,
        [{"role": "user", "content": "小米 14 怎么样？"}],
    )

    assert result.intent == "knowledge_query"
    assert result.need_retrieval is True
    assert "小米 14" in result.rewritten_question


def test_analysis_validates_and_infers_fields_omitted_by_compatible_json_mode() -> None:
    result = QuestionAnalysis.model_validate(
        {
            "intent": "knowledge_query",
            "rewritten_question": "Xiaomi 14 的电池容量是多少？",
            "product_models": ["Xiaomi 14"],
        }
    )

    assert result.need_retrieval is True
    assert result.confidence == 0.8
