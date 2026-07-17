from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request, Response, status
from sqlalchemy import delete, or_, select

from app.auth.dependencies import AdminOrOperatorDep, CurrentUserDep
from app.core.errors import AppError
from app.db.base import SessionDep
from app.db.models import (
    BehaviorEvent,
    Conversation,
    Feedback,
    Message,
    MessageRole,
    MockOrder,
    Ticket,
)
from app.ingestion.parsers import extract_product_models
from app.operations.analytics import build_user_profile, hot_topics
from app.operations.recommendation import recommend, train_recommender
from app.operations.schemas import (
    AuditEventResponse,
    ConversationLogItem,
    FeedbackAdminResponse,
    HotTopicList,
    MockOrderResponse,
    RecommendationList,
    TicketCreate,
    TicketResponse,
    TrainingRunResponse,
    UserProfileResponse,
)

router = APIRouter(tags=["operations"])


@router.get("/mock/orders")
def list_mock_orders(session: SessionDep, current_user: CurrentUserDep) -> list[MockOrderResponse]:
    orders = list(session.scalars(select(MockOrder).where(MockOrder.user_id == current_user.id)))
    return [MockOrderResponse.model_validate(order) for order in orders]


@router.post("/tickets", status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate, session: SessionDep, current_user: CurrentUserDep
) -> TicketResponse:
    conversation = session.get(Conversation, payload.conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise AppError(404, "conversation_not_found", "会话不存在")
    transcript = "\n".join(
        f"{message.role.value}: {message.content}" for message in conversation.messages
    )
    models = extract_product_models(transcript)
    ticket = Ticket(
        user_id=current_user.id,
        conversation_id=conversation.id,
        product_model=models[0] if models else None,
        summary=transcript[-2000:],
        attempted_solution=next(
            (
                message.content
                for message in reversed(conversation.messages)
                if message.role == MessageRole.assistant
            ),
            None,
        ),
        priority=payload.priority,
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return TicketResponse.model_validate(ticket)


@router.get("/tickets")
def list_tickets(session: SessionDep, _current_user: AdminOrOperatorDep) -> list[TicketResponse]:
    return [
        TicketResponse.model_validate(ticket)
        for ticket in session.scalars(select(Ticket).order_by(Ticket.created_at.desc()))
    ]


@router.get("/operations/hot-topics")
def get_hot_topics(
    session: SessionDep,
    _current_user: AdminOrOperatorDep,
    window: Annotated[Literal["day", "week", "month"], Query()] = "day",
) -> HotTopicList:
    return HotTopicList(window=window, items=hot_topics(session, window))


@router.get("/operations/profile/me")
def get_profile(session: SessionDep, current_user: CurrentUserDep) -> UserProfileResponse:
    return build_user_profile(session, current_user.id)


@router.delete("/operations/profile/me", status_code=204)
def clear_profile(session: SessionDep, current_user: CurrentUserDep) -> Response:
    session.execute(delete(BehaviorEvent).where(BehaviorEvent.user_id == current_user.id))
    session.commit()
    return Response(status_code=204)


@router.get("/recommendations")
def get_recommendations(
    knowledge_base_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> RecommendationList:
    return recommend(session, current_user.id, knowledge_base_id)


@router.post("/recommendation/training-runs", status_code=201)
def create_training_run(
    request: Request, session: SessionDep, _current_user: AdminOrOperatorDep
) -> TrainingRunResponse:
    run = train_recommender(session, request.app.state.settings.model_artifact_dir)
    return TrainingRunResponse.model_validate(run)


@router.get("/operations/logs")
def conversation_logs(
    session: SessionDep,
    _current_user: AdminOrOperatorDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> list[ConversationLogItem]:
    statement = select(Message).where(Message.role == MessageRole.assistant)
    if q:
        matching_conversations = select(Message.conversation_id).where(
            or_(Message.content.ilike(f"%{q}%"), Message.intent.ilike(f"%{q}%"))
        )
        statement = statement.where(Message.conversation_id.in_(matching_conversations))
    assistant_messages = list(
        session.scalars(statement.order_by(Message.created_at.desc()).limit(100))
    )
    items = []
    for answer in assistant_messages:
        question = session.scalar(
            select(Message.content)
            .where(
                Message.conversation_id == answer.conversation_id,
                Message.role == MessageRole.user,
                Message.created_at <= answer.created_at,
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        items.append(
            ConversationLogItem(
                message_id=answer.id,
                conversation_id=answer.conversation_id,
                question=question or "",
                answer=answer.content,
                intent=answer.intent,
                fallback=answer.fallback,
                latency_ms=answer.latency_ms,
                created_at=answer.created_at,
            )
        )
    return items


@router.get("/operations/feedback")
def list_feedback(
    session: SessionDep,
    _current_user: AdminOrOperatorDep,
    rating: Annotated[Literal["up", "down"] | None, Query()] = None,
) -> list[FeedbackAdminResponse]:
    statement = select(Feedback)
    if rating:
        statement = statement.where(Feedback.rating == rating)
    return [
        FeedbackAdminResponse.model_validate(item)
        for item in session.scalars(statement.order_by(Feedback.created_at.desc()).limit(100))
    ]


@router.get("/operations/audit")
def audit_events(
    session: SessionDep, _current_user: AdminOrOperatorDep
) -> list[AuditEventResponse]:
    statement = (
        select(BehaviorEvent)
        .where(BehaviorEvent.event_type.like("audit:%"))
        .order_by(BehaviorEvent.created_at.desc())
        .limit(100)
    )
    return [AuditEventResponse.model_validate(item) for item in session.scalars(statement)]
