import re
from collections.abc import Iterator
from time import perf_counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.advisor.schemas import (
    AdvisorCreateResponse,
    AdvisorPlanResponse,
    AdvisorSessionResponse,
    AdvisorSessionSummary,
    AdvisorTurnResponse,
)
from app.chat.schemas import AiTraceStep, SourceResponse
from app.core.config import Settings
from app.core.errors import AppError
from app.db.models import (
    AdvisorSession,
    AdvisorTurn,
    BehaviorEvent,
    Document,
    DocumentChunk,
    KnowledgeBase,
    User,
)
from app.rag.providers import (
    AdvisorRequirements,
    ChatProvider,
    QuestionAnalysis,
    create_chat_provider,
)
from app.rag.reranking import rerank_sources
from app.rag.retrieval import RetrievedSource, retrieve_sources
from app.rag.vector_store import VectorStoreService

CATEGORY_LABELS = {
    "phone": "手机",
    "tablet": "平板",
    "wearable": "智能穿戴",
    "robot_vacuum": "扫地机器人",
}
PRICE_PATTERN = re.compile(
    r"(?:售价|价格|起售价|首发价)\s*(?:为|：|:)?\s*[¥￥]?\s*(\d{2,6})\s*元|[¥￥]\s*(\d{2,6})"
)
DATE_PATTERN = re.compile(r"captured_at:\s*(\d{4}-\d{2}-\d{2})", re.IGNORECASE)


def model_identity(settings: Settings) -> tuple[str, str]:
    base_url = (settings.openai_base_url or "").lower()
    if settings.llm_provider == "mock":
        return "Mock AI", settings.llm_model
    if "deepseek" in settings.llm_model.lower() or "deepseek" in base_url:
        return "DeepSeek", settings.llm_model
    if settings.llm_provider == "ollama":
        return "Ollama", settings.llm_model
    return "OpenAI-compatible", settings.llm_model


def session_summary(item: AdvisorSession) -> AdvisorSessionSummary:
    return AdvisorSessionSummary(
        id=item.id,
        knowledge_base_id=item.knowledge_base_id,
        title=item.title,
        category=item.category,
        turn_count=len(item.turns),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def turn_response(item: AdvisorTurn) -> AdvisorTurnResponse:
    return AdvisorTurnResponse(
        id=item.id,
        sequence_no=item.sequence_no,
        question=item.question,
        requirements=item.requirements,
        plan=AdvisorPlanResponse.model_validate(item.plan) if item.plan else None,
        sources=[SourceResponse.model_validate(source) for source in item.sources],
        ai_trace=[AiTraceStep.model_validate(step) for step in item.ai_trace],
        status=item.status,
        created_at=item.created_at,
    )


def full_session_response(item: AdvisorSession) -> AdvisorSessionResponse:
    summary = session_summary(item)
    return AdvisorSessionResponse(
        **summary.model_dump(),
        turns=[turn_response(turn) for turn in item.turns],
    )


def get_owned_session(session: Session, session_id: str, user: User) -> AdvisorSession:
    item = session.get(AdvisorSession, session_id)
    if not item or item.user_id != user.id:
        raise AppError(404, "advisor_session_not_found", "选购会话不存在")
    return item


def create_session_record(
    session: Session,
    user: User,
    knowledge_base_id: str,
    category: str | None,
) -> AdvisorSession:
    if not session.get(KnowledgeBase, knowledge_base_id):
        raise AppError(404, "knowledge_base_not_found", "知识库不存在")
    label = CATEGORY_LABELS.get(category or "", "产品")
    item = AdvisorSession(
        user_id=user.id,
        knowledge_base_id=knowledge_base_id,
        category=category,
        title=f"{label} AI 选购方案",
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def validate_sensitive_input(
    db: Session,
    settings: Settings,
    user: User,
    text: str,
) -> None:
    matched = [word for word in settings.sensitive_words if word in text]
    if not matched:
        return
    db.add(
        BehaviorEvent(
            user_id=user.id,
            event_type="audit:blocked_input",
            payload={"matched_terms": matched, "action": "blocked"},
        )
    )
    db.commit()
    raise AppError(400, "sensitive_input", "输入包含不应提交的敏感凭据，请删除后重试")


def _persist_trace(session: Session, turn: AdvisorTurn, trace: list[AiTraceStep]) -> None:
    turn.ai_trace = [step.model_dump() for step in trace]
    session.add(turn)
    session.commit()


def _source_snapshot(session: Session, sources: list[RetrievedSource]) -> list[dict]:
    snapshots: list[dict] = []
    for source in sources:
        document = session.get(Document, source.document_id)
        snapshots.append(
            {
                "document_id": source.document_id,
                "chunk_id": source.chunk_id,
                "filename": source.filename,
                "location": source.location,
                "snippet": source.snippet,
                "score": source.score,
                "source_url": document.source_url if document else None,
            }
        )
    return snapshots


def _price_evidence(source_ids: list[str], sources: list[dict]) -> dict:
    for source in sources:
        if source["chunk_id"] not in source_ids:
            continue
        match = PRICE_PATTERN.search(source["snippet"])
        if not match:
            continue
        amount = next(value for value in match.groups() if value)
        date_match = DATE_PATTERN.search(source["snippet"])
        return {
            "status": "evidence",
            "display": f"资料标注价 ¥{amount}",
            "source_chunk_id": source["chunk_id"],
            "captured_at": date_match.group(1) if date_match else None,
        }
    return {
        "status": "unavailable",
        "display": "价格待官网确认",
        "source_chunk_id": None,
        "captured_at": None,
    }


def _ground_text(text: str, evidence: str) -> str:
    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    if numbers and any(number not in evidence for number in numbers):
        return "资料未明确"
    return text


def ground_plan(plan: dict, sources: list[dict]) -> dict:
    source_by_id = {source["chunk_id"]: source for source in sources}
    for candidate in plan["candidates"]:
        candidate_sources = [
            source_by_id[source_id]
            for source_id in candidate["source_chunk_ids"]
            if source_id in source_by_id
        ]
        evidence = "\n".join(source["snippet"] for source in candidate_sources)
        candidate["highlights"] = [_ground_text(text, evidence) for text in candidate["highlights"]]
        candidate["tradeoffs"] = [_ground_text(text, evidence) for text in candidate["tradeoffs"]]
        candidate["price"] = _price_evidence(candidate["source_chunk_ids"], sources)
    all_evidence = "\n".join(source["snippet"] for source in sources)
    for row in plan["comparison_rows"]:
        row["values"] = {
            model: _ground_text(value, all_evidence) for model, value in row["values"].items()
        }
    recommendation = plan["recommendation"]
    recommendation["summary"] = _ground_text(recommendation["summary"], all_evidence)
    recommendation["reasons"] = [
        _ground_text(reason, all_evidence) for reason in recommendation["reasons"]
    ]
    recommendation["caveats"] = [
        _ground_text(caveat, all_evidence) for caveat in recommendation["caveats"]
    ]
    plan["follow_up_suggestions"] = [
        _ground_text(suggestion, all_evidence) for suggestion in plan["follow_up_suggestions"]
    ]
    return plan


def create_chat_advisor_plan(
    db: Session,
    user: User,
    knowledge_base_id: str,
    question: str,
    analysis: QuestionAnalysis,
    provider: ChatProvider,
    sources: list,
    message_id: str,
    ai_trace: list[AiTraceStep],
) -> tuple[str, str, dict]:
    requirements = analysis.advisor_requirements or AdvisorRequirements(
        mode="comparison" if analysis.intent == "product_comparison" else "purchase_advice"
    )
    item = AdvisorSession(
        user_id=user.id,
        knowledge_base_id=knowledge_base_id,
        category=requirements.category,
        title=f"{CATEGORY_LABELS.get(requirements.category or '', '产品')} AI 选购方案",
    )
    snapshots = _source_snapshot(db, sources)
    evidence = []
    for source in sources:
        chunk = db.get(DocumentChunk, source.chunk_id)
        evidence.append(
            {
                "chunk_id": source.chunk_id,
                "filename": source.filename,
                "location": source.location,
                "snippet": source.snippet,
                "product_models": chunk.product_models if chunk else [],
            }
        )
    draft = provider.generate_advisor(analysis.rewritten_question, evidence)
    plan = ground_plan(draft.model_dump(), snapshots)
    turn = AdvisorTurn(
        message_id=message_id,
        sequence_no=1,
        question=question,
        requirements=requirements.model_dump(),
        plan=plan,
        sources=snapshots,
        ai_trace=[step.model_dump() for step in ai_trace],
        status="completed",
    )
    item.turns.append(turn)
    db.add(item)
    db.flush()
    return item.id, turn.id, plan


def sync_chat_advisor_trace(
    db: Session,
    turn_id: str | None,
    ai_trace: list[AiTraceStep],
) -> None:
    if not turn_id:
        return
    turn = db.get(AdvisorTurn, turn_id)
    if not turn:
        return
    turn.ai_trace = [step.model_dump() for step in ai_trace]
    db.add(turn)


def _merge_requirements(
    analyzed: AdvisorRequirements | None,
    overrides: dict,
    previous: dict | None,
) -> AdvisorRequirements:
    values = dict(previous or {})
    if analyzed:
        values.update(
            {
                key: value
                for key, value in analyzed.model_dump().items()
                if value not in (None, [], "")
            }
        )
    values.update(
        {key: value for key, value in overrides.items() if value not in (None, [], "auto")}
    )
    values.setdefault("mode", "purchase_advice")
    return AdvisorRequirements.model_validate(values)


def retrieve_advisor_sources(
    db: Session,
    vector_store: VectorStoreService,
    knowledge_base_id: str,
    query: str,
    product_models: list[str],
    threshold: float,
    require_lexical_overlap: bool,
) -> list[RetrievedSource]:
    queries = [query]
    queries.extend(
        model
        for model in product_models
        if model and model.casefold() not in {item.casefold() for item in queries}
    )
    source_by_id: dict[str, RetrievedSource] = {}
    for current_query in queries:
        results = retrieve_sources(
            db,
            vector_store,
            knowledge_base_id,
            current_query,
            top_k=12 if current_query == query else 6,
            threshold=threshold,
            require_lexical_overlap=require_lexical_overlap,
        )
        for source in results:
            existing = source_by_id.get(source.chunk_id)
            if not existing or source.score > existing.score:
                source_by_id[source.chunk_id] = source
    return sorted(source_by_id.values(), key=lambda item: item.score, reverse=True)[:12]


def advisor_events(
    db: Session,
    settings: Settings,
    vector_store: VectorStoreService,
    user: User,
    advisor_session: AdvisorSession,
    question: str,
    overrides: dict,
) -> Iterator[tuple[str, dict]]:
    sequence_no = len(advisor_session.turns) + 1
    turn = AdvisorTurn(
        session_id=advisor_session.id,
        sequence_no=sequence_no,
        question=question,
        requirements={},
        plan={},
        sources=[],
        ai_trace=[],
        status="running",
    )
    advisor_session.turns.append(turn)
    db.add(advisor_session)
    db.commit()
    db.refresh(turn)
    yield "meta", {"session_id": advisor_session.id, "turn_id": turn.id}

    provider: ChatProvider = create_chat_provider(settings)
    engine, model = model_identity(settings)
    trace: list[AiTraceStep] = []

    understanding_running = AiTraceStep(
        stage="understanding",
        status="running",
        engine=engine,
        model=model,
        summary="DeepSeek 调用 1/3：正在理解预算、用途和偏好",
    )
    trace.append(understanding_running)
    _persist_trace(db, turn, trace)
    yield "trace", understanding_running.model_dump()
    started = perf_counter()
    recent_messages: list[dict[str, str]] = []
    for previous_turn in advisor_session.turns[:-1]:
        recent_messages.extend(
            [
                {"role": "user", "content": previous_turn.question},
                {
                    "role": "assistant",
                    "content": previous_turn.plan.get("recommendation", {}).get("summary", ""),
                },
            ]
        )
    try:
        analysis = provider.analyze(question, recent_messages=recent_messages[-20:])
        analysis_status = "completed"
    except Exception:
        analysis = None
        analysis_status = "degraded"
    previous_requirements = advisor_session.turns[-2].requirements if sequence_no > 1 else None
    requirements = _merge_requirements(
        analysis.advisor_requirements if analysis else None,
        overrides,
        previous_requirements,
    )
    rewritten = analysis.rewritten_question if analysis else question
    query_parts = [rewritten, CATEGORY_LABELS.get(requirements.category or "", "")]
    query_parts.extend(overrides.get("product_models") or [])
    query = " ".join(part for part in query_parts if part)
    turn.requirements = requirements.model_dump()
    trace[0] = AiTraceStep(
        stage="understanding",
        status=analysis_status,
        engine=engine,
        model=model,
        duration_ms=int((perf_counter() - started) * 1000),
        summary=f"识别为{CATEGORY_LABELS.get(requirements.category or '', '产品')}选购需求",
        details=[
            f"检索问题：{query[:120]}",
            f"关注维度：{'、'.join(requirements.priorities) or '综合'}",
        ],
    )
    _persist_trace(db, turn, trace)
    yield "trace", trace[0].model_dump()

    retrieval_running = AiTraceStep(
        stage="retrieval",
        status="running",
        engine="BGE" if settings.embedding_provider == "bge" else "Embedding",
        model=settings.embedding_model,
        summary="正在召回产品候选和参数证据",
    )
    trace.append(retrieval_running)
    _persist_trace(db, turn, trace)
    yield "trace", retrieval_running.model_dump()
    started = perf_counter()
    requested_models = list(overrides.get("product_models") or [])
    if analysis:
        requested_models.extend(analysis.product_models)
    requested_models = list(dict.fromkeys(requested_models))[:4]
    candidates = retrieve_advisor_sources(
        db,
        vector_store,
        advisor_session.knowledge_base_id,
        query,
        requested_models,
        threshold=settings.similarity_threshold,
        require_lexical_overlap=settings.embedding_provider == "mock",
    )
    trace[1] = AiTraceStep(
        stage="retrieval",
        status="completed",
        engine=retrieval_running.engine,
        model=retrieval_running.model,
        duration_ms=int((perf_counter() - started) * 1000),
        summary=f"召回 {len(candidates)} 个候选知识片段",
    )
    _persist_trace(db, turn, trace)
    yield "trace", trace[1].model_dump()

    rerank_running = AiTraceStep(
        stage="reranking",
        status="running" if candidates else "skipped",
        engine=engine,
        model=model,
        summary=(
            f"DeepSeek 调用 2/3：正在筛选 {len(candidates)} 个候选片段"
            if candidates
            else "DeepSeek #2 已跳过：没有召回候选资料"
        ),
    )
    trace.append(rerank_running)
    _persist_trace(db, turn, trace)
    yield "trace", rerank_running.model_dump()
    selected: list[RetrievedSource] = []
    if candidates:
        started = perf_counter()
        selected, status, summary, details = rerank_sources(
            provider,
            query,
            candidates,
            top_k=6,
            min_score=settings.rerank_min_score,
        )
        trace[2] = AiTraceStep(
            stage="reranking",
            status=status,
            engine=engine,
            model=model,
            duration_ms=int((perf_counter() - started) * 1000),
            summary=summary,
            details=details,
        )
        _persist_trace(db, turn, trace)
        yield "trace", trace[2].model_dump()

    generation = AiTraceStep(
        stage="generation",
        status="running" if selected else "skipped",
        engine=engine,
        model=model,
        summary=(
            "DeepSeek 调用 3/3：正在生成结构化对比与推荐方案"
            if selected
            else "DeepSeek #3 已跳过：没有可靠产品证据"
        ),
    )
    trace.append(generation)
    _persist_trace(db, turn, trace)
    yield "trace", generation.model_dump()
    plan: dict = {}
    snapshots = _source_snapshot(db, selected)
    if selected:
        evidence = []
        for source in selected:
            chunk = db.get(DocumentChunk, source.chunk_id)
            evidence.append(
                {
                    "chunk_id": source.chunk_id,
                    "filename": source.filename,
                    "location": source.location,
                    "snippet": source.snippet,
                    "product_models": chunk.product_models if chunk else [],
                }
            )
        started = perf_counter()
        try:
            draft = provider.generate_advisor(query, evidence)
            plan = draft.model_dump()
            generation_status = "completed"
            generation_summary = f"生成 {len(draft.candidates)} 个候选产品方案"
        except Exception:
            generation_status = "failed"
            generation_summary = "结构化选购方案生成失败"
        trace[3] = AiTraceStep(
            stage="generation",
            status=generation_status,
            engine=engine,
            model=model,
            duration_ms=int((perf_counter() - started) * 1000),
            summary=generation_summary,
        )
        _persist_trace(db, turn, trace)
        yield "trace", trace[3].model_dump()

    grounding_running = AiTraceStep(
        stage="grounding",
        status="running" if plan else "skipped",
        engine="Citation Guard",
        model="deterministic-grounding-v1",
        summary="正在核验型号、数字参数、价格和引用",
    )
    trace.append(grounding_running)
    _persist_trace(db, turn, trace)
    yield "trace", grounding_running.model_dump()
    if plan:
        plan = ground_plan(plan, snapshots)
        trace[4] = AiTraceStep(
            stage="grounding",
            status="completed",
            engine="Citation Guard",
            model="deterministic-grounding-v1",
            duration_ms=0,
            summary=f"已核验 {len(snapshots)} 个真实来源，未使用无依据价格",
        )
    turn.plan = plan
    turn.sources = snapshots
    turn.status = "completed" if plan else "no_evidence"
    turn.ai_trace = [step.model_dump() for step in trace]
    advisor_session.category = requirements.category or advisor_session.category
    db.add_all([turn, advisor_session])
    db.commit()
    yield "trace", trace[4].model_dump()
    yield "advisor", {"plan": plan or None, "turn_id": turn.id}
    yield "sources", {"sources": snapshots}
    yield "done", {"status": turn.status}


def consume_advisor_events(events: Iterator[tuple[str, dict]]) -> None:
    for _event, _payload in events:
        pass


def create_response(item: AdvisorSession) -> AdvisorCreateResponse:
    return AdvisorCreateResponse(
        session=session_summary(item),
        turn=turn_response(item.turns[-1]),
    )


def list_session_summaries(db: Session, user: User) -> list[AdvisorSessionSummary]:
    items = db.scalars(
        select(AdvisorSession)
        .where(AdvisorSession.user_id == user.id)
        .order_by(AdvisorSession.updated_at.desc())
    ).all()
    return [session_summary(item) for item in items]


def next_sequence_number(db: Session, session_id: str) -> int:
    return (
        db.scalar(
            select(func.max(AdvisorTurn.sequence_no)).where(AdvisorTurn.session_id == session_id)
        )
        or 0
    ) + 1
