from time import perf_counter
from uuid import uuid4

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
    User,
)
from app.rag.providers import create_chat_provider
from app.rag.retrieval import retrieve_sources
from app.rag.vector_store import VectorStoreService

FALLBACK_ANSWER = "未找到可靠依据。请换一种问法、补充具体产品型号，或联系人工客服。"


def classify_intent(text: str) -> str:
    if any(keyword in text for keyword in ("订单", "物流", "快递", "发货")):
        return "tool_use"
    if any(keyword in text.lower() for keyword in ("你好", "谢谢", "hello")):
        return "general_chat"
    return "knowledge_query"


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
    conversation = get_or_create_conversation(
        session, user, knowledge_base_id, conversation_id
    )
    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.user,
        content=question.strip(),
    )
    session.add(user_message)
    session.flush()
    compact_history(conversation)
    sources = retrieve_sources(
        session,
        vector_store,
        knowledge_base_id,
        question,
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
    conversation.consecutive_fallbacks = (
        conversation.consecutive_fallbacks + 1 if fallback else 0
    )
    run_id = str(uuid4())
    assistant_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.assistant,
        content=answer,
        run_id=run_id,
        intent=classify_intent(question),
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

