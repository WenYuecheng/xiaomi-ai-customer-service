from time import perf_counter
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

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
from app.rag.providers import create_chat_provider
from app.rag.retrieval import retrieve_sources
from app.rag.vector_store import VectorStoreService

FALLBACK_ANSWER = "未找到可靠依据。请换一种问法、补充具体产品型号，或联系人工客服。"


def classify_intent(text: str) -> str:
    if any(keyword in text for keyword in ("转人工", "人工客服", "人工处理")):
        return "human_transfer"
    if any(keyword in text for keyword in ("订单", "物流", "快递", "发货")):
        return "tool_use"
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


def complete_chat(
    session: Session,
    settings: Settings,
    vector_store: VectorStoreService,
    user: User,
    knowledge_base_id: str,
    question: str,
    conversation_id: str | None,
) -> tuple[Conversation, Message, list[MessageSource], str]:
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
    retrieval_question = rewrite_question(question, conversation)
    intent = classify_intent(question)
    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.user,
        content=question.strip(),
    )
    session.add(user_message)
    session.flush()
    compact_history(conversation)
    sources = []
    if intent == "knowledge_query":
        sources = retrieve_sources(
            session,
            vector_store,
            knowledge_base_id,
            retrieval_question,
            settings.top_k,
            settings.similarity_threshold,
            require_lexical_overlap=settings.embedding_provider == "mock",
        )
        fallback = not sources
        answer = FALLBACK_ANSWER
        if sources:
            answer = create_chat_provider(settings).generate(
                question, [source.snippet for source in sources], conversation.summary
            )
    else:
        answer, fallback = answer_business_intent(session, user, intent)
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
    session.add(
        BehaviorEvent(
            user_id=user.id,
            event_type="chat",
            payload={
                "question": question,
                "intent": assistant_message.intent,
                "fallback": fallback,
                "knowledge_base_id": knowledge_base_id,
            },
        )
    )
    session.commit()
    return conversation, assistant_message, source_models, run_id
