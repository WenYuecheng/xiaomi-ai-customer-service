import json
from collections.abc import Iterable

from fastapi import APIRouter, Request, Response
from sqlalchemy import select
from starlette.responses import StreamingResponse

from app.auth.dependencies import CurrentUserDep
from app.chat.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    FeedbackRequest,
    FeedbackResponse,
    MessageResponse,
    SourceResponse,
)
from app.chat.service import complete_chat, prepare_chat, stream_prepared_chat
from app.core.errors import AppError
from app.db.base import SessionDep
from app.db.models import (
    BehaviorEvent,
    Conversation,
    Feedback,
    FeedbackRating,
    Message,
    MessageRole,
)

router = APIRouter(tags=["chat"])


def build_chat_response(conversation, message, sources, run_id: str, ai_trace) -> ChatResponse:
    return ChatResponse(
        conversation_id=conversation.id,
        message_id=message.id,
        run_id=run_id,
        answer=message.content,
        sources=[SourceResponse.model_validate(source) for source in sources],
        fallback=message.fallback,
        transfer_suggested=(
            conversation.consecutive_fallbacks >= 2 or message.intent == "human_transfer"
        ),
        ai_trace=ai_trace,
    )


@router.post("/chat/completions", response_model=None)
def chat_completion(
    request: Request,
    payload: ChatRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ChatResponse | StreamingResponse:
    if payload.stream:
        prepared = prepare_chat(
            session,
            request.app.state.settings,
            request.app.state.worker.vector_store,
            current_user,
            payload.knowledge_base_id,
            payload.message,
            payload.conversation_id,
        )
        conversation, message, sources, run_id, ai_trace = (
            prepared.conversation,
            prepared.message,
            prepared.sources,
            prepared.run_id,
            prepared.ai_trace,
        )
    else:
        conversation, message, sources, run_id, ai_trace = complete_chat(
            session,
            request.app.state.settings,
            request.app.state.worker.vector_store,
            current_user,
            payload.knowledge_base_id,
            payload.message,
            payload.conversation_id,
        )
    response = build_chat_response(conversation, message, sources, run_id, ai_trace)
    if not payload.stream:
        return response

    def encode_event(event: str, data: dict) -> bytes:
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return f"event: {event}\ndata: {payload}\n\n".encode()

    def events() -> Iterable[bytes]:
        yield encode_event(
            "meta",
            {
                "conversation_id": response.conversation_id,
                "message_id": response.message_id,
                "run_id": response.run_id,
            },
        )
        for step in prepared.ai_trace:
            if step.stage != "grounding":
                yield encode_event("trace", step.model_dump())
        try:
            for token in stream_prepared_chat(
                session,
                request.app.state.settings,
                prepared,
                lambda: run_id in request.app.state.cancelled_runs,
            ):
                yield encode_event("delta", {"content": token})
        except Exception:
            generation = next(step for step in prepared.ai_trace if step.stage == "generation")
            yield encode_event("trace", generation.model_dump())
            yield encode_event("error", {"code": "generation_failed", "message": "回答生成失败"})
            return
        yield encode_event(
            "sources", {"sources": [source.model_dump() for source in response.sources]}
        )
        generation = next(step for step in prepared.ai_trace if step.stage == "generation")
        grounding = next(step for step in prepared.ai_trace if step.stage == "grounding")
        yield encode_event("trace", generation.model_dump())
        yield encode_event("trace", grounding.model_dump())
        yield encode_event(
            "done",
            {
                "fallback": response.fallback,
                "transfer_suggested": response.transfer_suggested,
                "cancelled": run_id in request.app.state.cancelled_runs,
            },
        )
        request.app.state.cancelled_runs.discard(run_id)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/chat/runs/{run_id}/cancel")
def cancel_run(request: Request, run_id: str, _current_user: CurrentUserDep) -> dict[str, bool]:
    request.app.state.cancelled_runs.add(run_id)
    return {"cancelled": True}


@router.get("/conversations/{conversation_id}")
def conversation_history(
    conversation_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ConversationResponse:
    conversation = session.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise AppError(404, "conversation_not_found", "会话不存在")
    trace_events = session.scalars(
        select(BehaviorEvent).where(
            BehaviorEvent.user_id == current_user.id,
            BehaviorEvent.event_type == "chat",
        )
    ).all()
    traces_by_message_id = {
        event.payload.get("message_id"): event.payload.get("ai_trace", [])
        for event in trace_events
        if event.payload.get("message_id")
    }
    messages = [
        MessageResponse(
            id=message.id,
            role=message.role.value,
            content=message.content,
            fallback=message.fallback,
            created_at=message.created_at,
            sources=[SourceResponse.model_validate(source) for source in message.sources],
            ai_trace=traces_by_message_id.get(message.id, []),
        )
        for message in conversation.messages
    ]
    return ConversationResponse(
        id=conversation.id,
        knowledge_base_id=conversation.knowledge_base_id,
        summary=conversation.summary,
        messages=messages,
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
def clear_conversation(
    conversation_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    conversation = session.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise AppError(404, "conversation_not_found", "会话不存在")
    session.delete(conversation)
    session.commit()
    return Response(status_code=204)


@router.post("/chat/feedback")
def submit_feedback(
    payload: FeedbackRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> FeedbackResponse:
    message = session.get(Message, payload.message_id)
    if (
        not message
        or message.role != MessageRole.assistant
        or message.conversation.user_id != current_user.id
    ):
        raise AppError(404, "message_not_found", "消息不存在")
    feedback = session.scalar(
        select(Feedback).where(
            Feedback.message_id == payload.message_id,
            Feedback.user_id == current_user.id,
        )
    )
    if not feedback:
        feedback = Feedback(message_id=payload.message_id, user_id=current_user.id)
        session.add(feedback)
    feedback.rating = FeedbackRating(payload.rating)
    feedback.correction = payload.correction
    session.commit()
    session.refresh(feedback)
    return FeedbackResponse.model_validate(feedback)
