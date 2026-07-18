from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from time import perf_counter
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.schemas import AiTraceStep
from app.core.config import Settings
from app.core.errors import AppError
from app.db.models import (
    BehaviorEvent,
    Conversation,
    KnowledgeBase,
    Message,
    MessageRole,
    MessageSource,
    MockOrder,
    User,
)
from app.rag.providers import (
    ChatProvider,
    QuestionAnalysis,
    RerankCandidate,
    create_chat_provider,
)
from app.rag.retrieval import retrieve_sources
from app.rag.vector_store import VectorStoreService

FALLBACK_ANSWER = "未找到可靠依据。请换一种问法、补充具体产品型号，或联系人工客服。"
INTENT_LABELS = {
    "knowledge_query": "知识咨询",
    "product_comparison": "产品对比",
    "purchase_advice": "选购建议",
    "troubleshooting": "故障诊断",
    "order_query": "订单查询",
    "human_transfer": "转人工",
    "general_chat": "普通聊天",
}


@dataclass
class PreparedChat:
    user: User
    knowledge_base_id: str
    original_question: str
    conversation: Conversation
    message: Message
    sources: list[MessageSource]
    run_id: str
    question: str
    contexts: list[str]
    recent_messages: list[dict[str, str]]
    started: float
    requires_generation: bool
    provider: ChatProvider
    behavior_event: BehaviorEvent
    ai_trace: list[AiTraceStep]


def classify_intent(text: str) -> str:
    if any(keyword in text for keyword in ("转人工", "人工客服", "人工处理")):
        return "human_transfer"
    if any(keyword in text for keyword in ("订单", "物流", "快递", "发货")):
        return "order_query"
    if any(keyword in text.lower() for keyword in ("你好", "谢谢", "hello")):
        return "general_chat"
    return "knowledge_query"


def rewrite_question(question: str, conversation: Conversation) -> str:
    """Resolve a small, deterministic set of follow-up references for retrieval."""
    references_previous = any(
        marker in question for marker in ("它", "这个", "该型号", "那款", "Pro 版", "标准版")
    )
    if not references_previous:
        return question
    previous_questions = [
        message.content for message in conversation.messages if message.role == MessageRole.user
    ]
    return f"{previous_questions[-1]}；追问：{question}" if previous_questions else question


def answer_business_intent(session: Session, user: User, intent: str) -> tuple[str, bool]:
    if intent == "general_chat":
        return "你好，我可以解答产品问题、查询演示订单，或协助转人工。", False
    if intent == "human_transfer":
        return "已为你准备转人工入口，请确认问题摘要后创建工单。", False
    order = session.scalar(
        select(MockOrder).where(MockOrder.user_id == user.id).order_by(MockOrder.created_at.desc())
    )
    if not order:
        return "未找到你的演示订单。当前系统未连接真实小米订单系统。", True
    latest = order.logistics[-1] if order.logistics else order.shipping_status
    return (
        f"【Mock 演示数据】订单 {order.order_no}，商品为 {order.product_name}，"
        f"支付状态：{order.payment_status}，物流状态：{latest}。"
    ), False


def model_identity(settings: Settings) -> tuple[str, str]:
    if settings.llm_provider == "mock":
        return "Mock AI", settings.llm_model
    if "deepseek" in settings.llm_model.lower() or "deepseek" in settings.openai_base_url.lower():
        return "DeepSeek", settings.llm_model
    if settings.llm_provider == "ollama":
        return "Ollama", settings.llm_model
    return "OpenAI-compatible", settings.llm_model


def fallback_analysis(question: str, conversation: Conversation) -> QuestionAnalysis:
    intent = classify_intent(question)
    return QuestionAnalysis(
        intent=intent,
        rewritten_question=rewrite_question(question, conversation),
        product_models=[],
        need_retrieval=intent
        in {"knowledge_query", "product_comparison", "purchase_advice", "troubleshooting"},
        confidence=0,
    )


def upsert_trace(prepared: PreparedChat, step: AiTraceStep) -> None:
    for index, current in enumerate(prepared.ai_trace):
        if current.stage == step.stage:
            prepared.ai_trace[index] = step
            return
    prepared.ai_trace.append(step)


def persist_trace(session: Session, prepared: PreparedChat) -> None:
    prepared.behavior_event.payload = {
        **prepared.behavior_event.payload,
        "ai_trace": [step.model_dump() for step in prepared.ai_trace],
    }
    session.commit()


def rerank_sources(
    provider: ChatProvider,
    question: str,
    candidates,
    top_k: int,
    min_score: float,
) -> tuple[list, str, str, list[str]]:
    try:
        result = provider.rerank(
            question,
            [
                RerankCandidate(
                    chunk_id=item.chunk_id,
                    filename=item.filename,
                    location=item.location,
                    snippet=item.snippet,
                    retrieval_score=item.score,
                )
                for item in candidates
            ],
            top_k,
        )
    except Exception:
        selected = candidates[:top_k]
        return (
            selected,
            "degraded",
            f"AI 重排不可用，已降级使用原始排序并保留 {len(selected)} 个片段",
            ["重排结果解析失败或包含非法候选 ID"],
        )
    candidate_by_id = {item.chunk_id: item for item in candidates}
    selected = [
        replace(candidate_by_id[decision.chunk_id], score=round(decision.relevance_score, 4))
        for decision in result.decisions
        if decision.relevance_score >= min_score
    ][:top_k]
    details = [
        (
            f"保留 {candidate_by_id[item.chunk_id].filename}：{item.reason}"
            if item.relevance_score >= min_score
            else f"排除 {candidate_by_id[item.chunk_id].filename}：{item.reason}"
        )
        for item in result.decisions[:3]
    ]
    return (
        selected,
        "completed",
        f"从 {len(candidates)} 个候选中保留 {len(selected)} 个可靠片段"
        if selected
        else f"检查 {len(candidates)} 个候选后未保留可靠片段",
        details,
    )


def get_or_create_conversation(
    session: Session, user: User, knowledge_base_id: str, conversation_id: str | None
) -> Conversation:
    if not session.get(KnowledgeBase, knowledge_base_id):
        raise AppError(404, "knowledge_base_not_found", "知识库不存在")
    if conversation_id:
        conversation = session.get(Conversation, conversation_id)
        if not conversation or conversation.user_id != user.id:
            raise AppError(404, "conversation_not_found", "会话不存在")
        if conversation.knowledge_base_id != knowledge_base_id:
            raise AppError(409, "conversation_knowledge_mismatch", "会话与知识库不匹配")
        return conversation
    conversation = Conversation(user_id=user.id, knowledge_base_id=knowledge_base_id)
    session.add(conversation)
    session.flush()
    return conversation


def compact_history(conversation: Conversation) -> None:
    if len(conversation.messages) <= 20:
        return
    older = conversation.messages[:-10]
    if len(older) <= conversation.summary_message_count:
        return
    summary_lines = [f"{message.role.value}: {message.content[:300]}" for message in older]
    conversation.summary = ("\n".join(summary_lines))[-4000:]
    conversation.summary_message_count = len(older)


def initialize_stream_chat(
    session: Session,
    settings: Settings,
    user: User,
    knowledge_base_id: str,
    question: str,
    conversation_id: str | None,
) -> PreparedChat:
    started = perf_counter()
    matched_sensitive_words = [word for word in settings.sensitive_words if word in question]
    if matched_sensitive_words:
        session.add(
            BehaviorEvent(
                user_id=user.id,
                event_type="audit:blocked_input",
                payload={"matched_terms": matched_sensitive_words, "action": "blocked"},
            )
        )
        session.commit()
        raise AppError(400, "sensitive_input", "输入包含不应提交的敏感凭据，请删除后重试")
    conversation = get_or_create_conversation(session, user, knowledge_base_id, conversation_id)
    recent_messages = [
        {"role": item.role.value, "content": item.content} for item in conversation.messages[-20:]
    ]
    session.add(
        Message(
            conversation_id=conversation.id,
            role=MessageRole.user,
            content=question.strip(),
        )
    )
    session.flush()
    compact_history(conversation)
    run_id = str(uuid4())
    assistant_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.assistant,
        content="",
        run_id=run_id,
        intent="knowledge_query",
        fallback=True,
        latency_ms=0,
    )
    session.add(assistant_message)
    session.flush()
    behavior_event = BehaviorEvent(
        user_id=user.id,
        event_type="chat",
        payload={
            "message_id": assistant_message.id,
            "question": question,
            "intent": "knowledge_query",
            "fallback": True,
            "knowledge_base_id": knowledge_base_id,
            "ai_trace": [],
        },
    )
    session.add(behavior_event)
    session.commit()
    return PreparedChat(
        user=user,
        knowledge_base_id=knowledge_base_id,
        original_question=question,
        conversation=conversation,
        message=assistant_message,
        sources=[],
        run_id=run_id,
        question=question,
        contexts=[],
        recent_messages=recent_messages,
        started=started,
        requires_generation=False,
        provider=create_chat_provider(settings),
        behavior_event=behavior_event,
        ai_trace=[],
    )


def stream_preparation_steps(
    session: Session,
    settings: Settings,
    vector_store: VectorStoreService,
    prepared: PreparedChat,
) -> Iterator[AiTraceStep]:
    engine, model = model_identity(settings)
    running = AiTraceStep(
        stage="understanding",
        status="running",
        engine=engine,
        model=model,
        summary="DeepSeek 调用 1/3：正在结合会话理解问题",
    )
    upsert_trace(prepared, running)
    persist_trace(session, prepared)
    yield running
    analysis_started = perf_counter()
    try:
        analysis = prepared.provider.analyze(
            prepared.original_question,
            prepared.conversation.summary,
            prepared.recent_messages,
        )
        understanding = AiTraceStep(
            stage="understanding",
            status="completed",
            engine=engine,
            model=model,
            duration_ms=int((perf_counter() - analysis_started) * 1000),
            summary=(
                f"识别意图：{INTENT_LABELS[analysis.intent]}；"
                f"检索问题：{analysis.rewritten_question}"
            ),
        )
    except Exception:
        intent = classify_intent(prepared.original_question)
        rewritten = prepared.original_question
        if any(
            marker in prepared.original_question
            for marker in ("它", "这个", "该型号", "那款", "Pro 版", "标准版")
        ):
            previous = [
                item["content"]
                for item in prepared.recent_messages
                if item["role"] == MessageRole.user.value
            ]
            if previous:
                rewritten = f"{previous[-1]}；追问：{prepared.original_question}"
        analysis = QuestionAnalysis(
            intent=intent,
            rewritten_question=rewritten,
            product_models=[],
            need_retrieval=intent
            in {"knowledge_query", "product_comparison", "purchase_advice", "troubleshooting"},
            confidence=0,
        )
        understanding = AiTraceStep(
            stage="understanding",
            status="degraded",
            engine=engine,
            model=model,
            duration_ms=int((perf_counter() - analysis_started) * 1000),
            summary=f"AI 理解不可用，已降级为规则；检索问题：{rewritten}",
        )
    prepared.question = analysis.rewritten_question
    prepared.message.intent = analysis.intent
    upsert_trace(prepared, understanding)
    persist_trace(session, prepared)
    yield understanding

    retrieval_running = AiTraceStep(
        stage="retrieval",
        status="running" if analysis.need_retrieval else "skipped",
        engine="BGE" if settings.embedding_provider == "bge" else "Embedding",
        model=settings.embedding_model,
        duration_ms=0 if not analysis.need_retrieval else None,
        summary=(
            "正在召回候选知识片段"
            if analysis.need_retrieval
            else "该意图由确定性业务流程处理，无需检索知识库"
        ),
    )
    upsert_trace(prepared, retrieval_running)
    persist_trace(session, prepared)
    yield retrieval_running
    candidates = []
    if analysis.need_retrieval:
        retrieval_started = perf_counter()
        candidates = retrieve_sources(
            session,
            vector_store,
            prepared.knowledge_base_id,
            analysis.rewritten_question,
            settings.rerank_candidate_k,
            settings.similarity_threshold,
            require_lexical_overlap=settings.embedding_provider == "mock",
        )
        retrieval_completed = AiTraceStep(
            stage="retrieval",
            status="completed",
            engine="BGE" if settings.embedding_provider == "bge" else "Embedding",
            model=settings.embedding_model,
            duration_ms=int((perf_counter() - retrieval_started) * 1000),
            summary=f"召回 {len(candidates)} 个候选知识片段",
        )
        upsert_trace(prepared, retrieval_completed)
        persist_trace(session, prepared)
        yield retrieval_completed

    selected = []
    if candidates:
        reranking_running = AiTraceStep(
            stage="reranking",
            status="running",
            engine=engine,
            model=model,
            summary=f"DeepSeek 调用 2/3：正在比较 {len(candidates)} 个候选片段",
        )
        upsert_trace(prepared, reranking_running)
        persist_trace(session, prepared)
        yield reranking_running
        reranking_started = perf_counter()
        selected, reranking_status, reranking_summary, reranking_details = rerank_sources(
            prepared.provider,
            analysis.rewritten_question,
            candidates,
            settings.top_k,
            settings.rerank_min_score,
        )
        reranking_completed = AiTraceStep(
            stage="reranking",
            status=reranking_status,
            engine=engine,
            model=model,
            duration_ms=int((perf_counter() - reranking_started) * 1000),
            summary=reranking_summary,
            details=reranking_details,
        )
    else:
        reranking_completed = AiTraceStep(
            stage="reranking",
            status="skipped",
            engine=engine,
            model=model,
            duration_ms=0,
            summary=(
                "DeepSeek #2 已跳过：BGE 没有召回候选片段"
                if analysis.need_retrieval
                else "DeepSeek #2 已跳过：该意图无需知识重排"
            ),
        )
    upsert_trace(prepared, reranking_completed)
    persist_trace(session, prepared)
    yield reranking_completed

    if analysis.need_retrieval:
        answer = "" if selected else FALLBACK_ANSWER
        fallback = not selected
    else:
        answer, fallback = answer_business_intent(session, prepared.user, analysis.intent)
    prepared.requires_generation = bool(selected)
    prepared.contexts = [source.snippet for source in selected]
    prepared.message.content = answer
    prepared.message.fallback = fallback
    prepared.conversation.consecutive_fallbacks = (
        prepared.conversation.consecutive_fallbacks + 1 if fallback else 0
    )
    source_models = [
        MessageSource(message_id=prepared.message.id, **source.__dict__) for source in selected
    ]
    session.add_all(source_models)
    prepared.sources = source_models
    generation = AiTraceStep(
        stage="generation",
        status="running" if selected else "skipped",
        engine=engine,
        model=model,
        duration_ms=None if selected else 0,
        summary=(
            "DeepSeek 调用 3/3：正在依据重排后的可靠片段生成回答"
            if selected
            else (
                "DeepSeek #3 已跳过：AI 重排后没有可靠依据"
                if analysis.need_retrieval
                else "DeepSeek #3 已跳过：使用确定性业务结果"
            )
        ),
    )
    upsert_trace(prepared, generation)
    grounding = AiTraceStep(
        stage="grounding",
        status="running" if selected else ("completed" if analysis.need_retrieval else "skipped"),
        engine="引用校验",
        model="source-grounding-v1",
        duration_ms=None if selected else 0,
        summary=(
            "等待回答完成后校验引用"
            if selected
            else (
                "没有可靠来源，已阻止事实性生成"
                if analysis.need_retrieval
                else "业务结果无需知识引用"
            )
        ),
    )
    upsert_trace(prepared, grounding)
    prepared.behavior_event.payload = {
        **prepared.behavior_event.payload,
        "intent": analysis.intent,
        "fallback": fallback,
    }
    prepared.message.latency_ms = int((perf_counter() - prepared.started) * 1000)
    persist_trace(session, prepared)
    yield generation


def prepare_chat(
    session: Session,
    settings: Settings,
    vector_store: VectorStoreService,
    user: User,
    knowledge_base_id: str,
    question: str,
    conversation_id: str | None,
) -> PreparedChat:
    started = perf_counter()
    matched_sensitive_words = [word for word in settings.sensitive_words if word in question]
    if matched_sensitive_words:
        session.add(
            BehaviorEvent(
                user_id=user.id,
                event_type="audit:blocked_input",
                payload={"matched_terms": matched_sensitive_words, "action": "blocked"},
            )
        )
        session.commit()
        raise AppError(400, "sensitive_input", "输入包含不应提交的敏感凭据，请删除后重试")
    conversation = get_or_create_conversation(session, user, knowledge_base_id, conversation_id)
    recent_messages = [
        {"role": item.role.value, "content": item.content} for item in conversation.messages[-20:]
    ]
    provider = create_chat_provider(settings)
    trace: list[AiTraceStep] = []
    engine, model = model_identity(settings)
    analysis_started = perf_counter()
    try:
        analysis = provider.analyze(question, conversation.summary, recent_messages)
        understanding_status = "completed"
        understanding_summary = (
            f"识别意图：{INTENT_LABELS[analysis.intent]}；检索问题：{analysis.rewritten_question}"
        )
    except Exception:
        analysis = fallback_analysis(question, conversation)
        understanding_status = "degraded"
        understanding_summary = (
            f"AI 理解不可用，已降级为规则；检索问题：{analysis.rewritten_question}"
        )
    trace.append(
        AiTraceStep(
            stage="understanding",
            status=understanding_status,
            engine=engine,
            model=model,
            duration_ms=int((perf_counter() - analysis_started) * 1000),
            summary=understanding_summary,
        )
    )
    intent = analysis.intent
    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.user,
        content=question.strip(),
    )
    session.add(user_message)
    session.flush()
    compact_history(conversation)
    sources = []
    requires_generation = False
    if analysis.need_retrieval:
        retrieval_started = perf_counter()
        sources = retrieve_sources(
            session,
            vector_store,
            knowledge_base_id,
            analysis.rewritten_question,
            settings.rerank_candidate_k,
            settings.similarity_threshold,
            require_lexical_overlap=settings.embedding_provider == "mock",
        )
        trace.append(
            AiTraceStep(
                stage="retrieval",
                status="completed",
                engine="BGE" if settings.embedding_provider == "bge" else "Embedding",
                model=settings.embedding_model,
                duration_ms=int((perf_counter() - retrieval_started) * 1000),
                summary=f"召回 {len(sources)} 个可靠知识片段",
            )
        )
        if sources:
            reranking_started = perf_counter()
            sources, reranking_status, reranking_summary, reranking_details = rerank_sources(
                provider,
                analysis.rewritten_question,
                sources,
                settings.top_k,
                settings.rerank_min_score,
            )
            trace.append(
                AiTraceStep(
                    stage="reranking",
                    status=reranking_status,
                    engine=engine,
                    model=model,
                    duration_ms=int((perf_counter() - reranking_started) * 1000),
                    summary=reranking_summary,
                    details=reranking_details,
                )
            )
        else:
            trace.append(
                AiTraceStep(
                    stage="reranking",
                    status="skipped",
                    engine=engine,
                    model=model,
                    duration_ms=0,
                    summary="DeepSeek #2 已跳过：BGE 没有召回候选片段",
                )
            )
        fallback = not sources
        answer = FALLBACK_ANSWER
        if sources:
            answer = ""
            requires_generation = True
            trace.append(
                AiTraceStep(
                    stage="generation",
                    status="running",
                    engine=engine,
                    model=model,
                    summary="DeepSeek 调用 3/3：正在依据重排后的可靠片段生成回答",
                )
            )
        else:
            trace.append(
                AiTraceStep(
                    stage="generation",
                    status="skipped",
                    engine=engine,
                    model=model,
                    duration_ms=0,
                    summary="DeepSeek #3 已跳过：AI 重排后没有可靠依据",
                )
            )
    else:
        trace.append(
            AiTraceStep(
                stage="retrieval",
                status="skipped",
                engine="BGE" if settings.embedding_provider == "bge" else "Embedding",
                model=settings.embedding_model,
                duration_ms=0,
                summary="该意图由确定性业务流程处理，无需检索知识库",
            )
        )
        trace.append(
            AiTraceStep(
                stage="reranking",
                status="skipped",
                engine=engine,
                model=model,
                duration_ms=0,
                summary="DeepSeek #2 已跳过：该意图无需知识重排",
            )
        )
        answer, fallback = answer_business_intent(session, user, intent)
        trace.append(
            AiTraceStep(
                stage="generation",
                status="skipped",
                engine=engine,
                model=model,
                duration_ms=0,
                summary="DeepSeek #3 已跳过：使用确定性业务结果",
            )
        )
    conversation.consecutive_fallbacks = conversation.consecutive_fallbacks + 1 if fallback else 0
    run_id = str(uuid4())
    assistant_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.assistant,
        content=answer,
        run_id=run_id,
        intent=intent,
        fallback=fallback,
        latency_ms=int((perf_counter() - started) * 1000),
    )
    session.add(assistant_message)
    session.flush()
    source_models = [
        MessageSource(message_id=assistant_message.id, **source.__dict__) for source in sources
    ]
    session.add_all(source_models)
    trace.append(
        AiTraceStep(
            stage="grounding",
            status="running"
            if requires_generation
            else ("completed" if analysis.need_retrieval else "skipped"),
            engine="引用校验",
            model="source-grounding-v1",
            duration_ms=None if requires_generation else 0,
            summary=(
                "等待回答完成后校验引用"
                if requires_generation
                else (
                    "没有可靠来源，已阻止事实性生成"
                    if analysis.need_retrieval
                    else "业务结果无需知识引用"
                )
            ),
        )
    )
    behavior_event = BehaviorEvent(
        user_id=user.id,
        event_type="chat",
        payload={
            "message_id": assistant_message.id,
            "question": question,
            "intent": assistant_message.intent,
            "fallback": fallback,
            "knowledge_base_id": knowledge_base_id,
            "ai_trace": [step.model_dump() for step in trace],
        },
    )
    session.add(behavior_event)
    session.commit()
    return PreparedChat(
        user=user,
        knowledge_base_id=knowledge_base_id,
        original_question=question,
        conversation=conversation,
        message=assistant_message,
        sources=source_models,
        run_id=run_id,
        question=analysis.rewritten_question,
        contexts=[source.snippet for source in sources],
        recent_messages=recent_messages,
        started=started,
        requires_generation=requires_generation,
        provider=provider,
        behavior_event=behavior_event,
        ai_trace=trace,
    )


def finalize_answer(session: Session, prepared: PreparedChat, answer: str) -> None:
    prepared.message.content = answer
    prepared.message.latency_ms = int((perf_counter() - prepared.started) * 1000)
    session.commit()


def stream_prepared_chat(
    session: Session,
    settings: Settings,
    prepared: PreparedChat,
    is_cancelled: Callable[[], bool],
) -> Iterator[str]:
    if not prepared.requires_generation:
        for index in range(0, len(prepared.message.content), 12):
            if is_cancelled():
                return
            yield prepared.message.content[index : index + 12]
        return
    del settings
    parts: list[str] = []
    generation_started = perf_counter()
    try:
        for token in prepared.provider.stream(
            prepared.question,
            prepared.contexts,
            prepared.conversation.summary,
            prepared.recent_messages,
        ):
            if is_cancelled():
                break
            parts.append(token)
            yield token
    except Exception:
        upsert_trace(
            prepared,
            AiTraceStep(
                stage="generation",
                status="failed",
                engine=prepared.ai_trace[0].engine,
                model=prepared.ai_trace[0].model,
                duration_ms=int((perf_counter() - generation_started) * 1000),
                summary="回答生成失败，已保留检索结果",
            ),
        )
        finalize_answer(session, prepared, "".join(parts))
        persist_trace(session, prepared)
        raise
    else:
        finalize_answer(session, prepared, "".join(parts))
        cancelled = is_cancelled()
        upsert_trace(
            prepared,
            AiTraceStep(
                stage="generation",
                status="failed" if cancelled else "completed",
                engine=prepared.ai_trace[0].engine,
                model=prepared.ai_trace[0].model,
                duration_ms=int((perf_counter() - generation_started) * 1000),
                summary="生成已由用户停止" if cancelled else "DeepSeek 调用 3/3：可信回答生成完成",
            ),
        )
        upsert_trace(
            prepared,
            AiTraceStep(
                stage="grounding",
                status="completed",
                engine="引用校验",
                model="source-grounding-v1",
                duration_ms=0,
                summary=f"已确认回答仅采用 {len(prepared.sources)} 个实际检索来源",
            ),
        )
        persist_trace(session, prepared)


def complete_chat(
    session: Session,
    settings: Settings,
    vector_store: VectorStoreService,
    user: User,
    knowledge_base_id: str,
    question: str,
    conversation_id: str | None,
) -> tuple[Conversation, Message, list[MessageSource], str, list[AiTraceStep]]:
    prepared = prepare_chat(
        session,
        settings,
        vector_store,
        user,
        knowledge_base_id,
        question,
        conversation_id,
    )
    if prepared.requires_generation:
        generation_started = perf_counter()
        try:
            answer = prepared.provider.generate(
                prepared.question,
                prepared.contexts,
                prepared.conversation.summary,
                prepared.recent_messages,
            )
        except Exception:
            upsert_trace(
                prepared,
                AiTraceStep(
                    stage="generation",
                    status="failed",
                    engine=prepared.ai_trace[0].engine,
                    model=prepared.ai_trace[0].model,
                    duration_ms=int((perf_counter() - generation_started) * 1000),
                    summary="回答生成失败",
                ),
            )
            persist_trace(session, prepared)
            raise
        finalize_answer(session, prepared, answer)
        upsert_trace(
            prepared,
            AiTraceStep(
                stage="generation",
                status="completed",
                engine=prepared.ai_trace[0].engine,
                model=prepared.ai_trace[0].model,
                duration_ms=int((perf_counter() - generation_started) * 1000),
                summary="DeepSeek 调用 3/3：可信回答生成完成",
            ),
        )
        upsert_trace(
            prepared,
            AiTraceStep(
                stage="grounding",
                status="completed",
                engine="引用校验",
                model="source-grounding-v1",
                duration_ms=0,
                summary=f"已确认回答仅采用 {len(prepared.sources)} 个实际检索来源",
            ),
        )
        persist_trace(session, prepared)
    return (
        prepared.conversation,
        prepared.message,
        prepared.sources,
        prepared.run_id,
        prepared.ai_trace,
    )
