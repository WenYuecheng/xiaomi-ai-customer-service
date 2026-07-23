"""
文件职责：
定义问答交互（Chat）及会话管理相关的 HTTP 路由接口。

所属功能：
智能问答 -> 路由层。

外部入口：
- POST `/api/v1/chat/completions` 发起问答（支持流式和非流式）
- POST `/api/v1/chat/runs/{run_id}/cancel` 取消流式生成
- GET/DELETE `/api/v1/conversations/{id}` 获取会话历史/清空会话
- POST `/api/v1/chat/feedback` 提交大模型回答反馈 (顶踩)

主要流程：
接收 HTTP 请求 -> 验证用户身份(依赖注入) -> 解析输入载荷(Pydantic)
-> 调用底层 service 层逻辑完成核心业务 -> 组装视图模型并返回(或以 SSE 形式返回流式数据)。
"""

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
from app.chat.service import (
    complete_chat,
    initialize_stream_chat,
    stream_preparation_steps,
    stream_prepared_chat,
)
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
from app.knowledge.selection import link_ids, resolve_knowledge_base_ids

router = APIRouter(tags=["chat"])


def build_chat_response(
    conversation,
    message,
    sources,
    run_id: str,
    ai_trace,
    advisor_session_id: str | None,
    advisor_plan: dict | None,
) -> ChatResponse:
    """
    组装非流式情况下的完整响应对象。

    Args:
        conversation: 当前对话实体。
        message: 模型生成的回答消息。
        sources: 检索到的知识库来源。
        run_id: 本次生成的运行 ID。
        ai_trace: 执行轨迹列表。
        advisor_session_id: 顾问会话 ID（如果有）。
        advisor_plan: 顾问计划字典（如果有）。

    Returns:
        ChatResponse: 标准化的回复数据结构。
    """
    return ChatResponse(
        conversation_id=conversation.id,
        knowledge_base_id=conversation.knowledge_base_id,
        knowledge_base_ids=link_ids(
            conversation.knowledge_base_links, conversation.knowledge_base_id
        ),
        message_id=message.id,
        run_id=run_id,
        answer=message.content,
        sources=[SourceResponse.model_validate(source) for source in sources],
        fallback=message.fallback,
        transfer_suggested=(
            conversation.consecutive_fallbacks >= 2 or message.intent == "human_transfer"
        ),
        ai_trace=ai_trace,
        advisor_session_id=advisor_session_id,
        advisor_plan=advisor_plan,
    )


@router.post("/chat/completions", response_model=None)
def chat_completion(
    request: Request,
    payload: ChatRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ChatResponse | StreamingResponse:
    """
    发起聊天完成请求（问答接口）。

    功能：接收用户的核心提问，调用底层的检索与大模型生成流水线。

    支持机制：
    若 payload.stream=True，则返回 text/event-stream 的 SSE (Server-Sent Events) 流。
    会在流中推送分析过程 (trace)、逐字生成的回答 (delta) 及检索来源 (sources)。
    若 payload.stream=False，则等待全部生成完毕后返回统一的 ChatResponse。

    Args:
        request (Request): FastAPI 的 Request 对象。
        payload (ChatRequest): 客户端请求的数据。
        session (SessionDep): 数据库会话。
        current_user (CurrentUserDep): 当前已认证的用户对象。

    Returns:
        ChatResponse | StreamingResponse: 取决于是否开启流式传输。
    """
    knowledge_base_ids = resolve_knowledge_base_ids(
        payload.knowledge_base_id, payload.knowledge_base_ids
    )
    if payload.stream:
        prepared = initialize_stream_chat(
            session,
            request.app.state.settings,
            current_user,
            knowledge_base_ids,
            payload.message,
            payload.conversation_id,
        )
    else:
        (
            conversation,
            message,
            sources,
            run_id,
            ai_trace,
            advisor_session_id,
            advisor_plan,
        ) = complete_chat(
            session,
            request.app.state.settings,
            request.app.state.worker.vector_store,
            current_user,
            knowledge_base_ids,
            payload.message,
            payload.conversation_id,
        )
    if not payload.stream:
        return build_chat_response(
            conversation,
            message,
            sources,
            run_id,
            ai_trace,
            advisor_session_id,
            advisor_plan,
        )

    def encode_event(event: str, data: dict) -> bytes:
        """将事件名和数据序列化为 SSE 规定的字节流格式。"""
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return f"event: {event}\ndata: {payload}\n\n".encode()

    def events() -> Iterable[bytes]:
        """SSE 数据生成器，按步骤逐步产生事件。"""
        yield encode_event(
            "meta",
            {
                "conversation_id": prepared.conversation.id,
                "message_id": prepared.message.id,
                "run_id": prepared.run_id,
                "knowledge_base_id": prepared.knowledge_base_id,
                "knowledge_base_ids": prepared.knowledge_base_ids,
            },
        )
        for step in stream_preparation_steps(
            session,
            request.app.state.settings,
            request.app.state.worker.vector_store,
            prepared,
        ):
            yield encode_event("trace", step.model_dump())
        try:
            for token in stream_prepared_chat(
                session,
                request.app.state.settings,
                prepared,
                lambda: prepared.run_id in request.app.state.cancelled_runs,
            ):
                yield encode_event("delta", {"content": token})
        except Exception:
            generation = next(step for step in prepared.ai_trace if step.stage == "generation")
            yield encode_event("trace", generation.model_dump())
            yield encode_event("error", {"code": "generation_failed", "message": "回答生成失败"})
            return
        yield encode_event(
            "sources",
            {
                "sources": [
                    SourceResponse.model_validate(source).model_dump()
                    for source in prepared.sources
                ]
            },
        )
        if prepared.advisor_plan:
            yield encode_event(
                "advisor",
                {
                    "advisor_session_id": prepared.advisor_session_id,
                    "plan": prepared.advisor_plan,
                },
            )
        generation = next(step for step in prepared.ai_trace if step.stage == "generation")
        grounding = next(step for step in prepared.ai_trace if step.stage == "grounding")
        if prepared.requires_generation:
            yield encode_event("trace", generation.model_dump())
        yield encode_event("trace", grounding.model_dump())
        yield encode_event(
            "done",
            {
                "fallback": prepared.message.fallback,
                "transfer_suggested": (
                    prepared.conversation.consecutive_fallbacks >= 2
                    or prepared.message.intent == "human_transfer"
                ),
                "cancelled": prepared.run_id in request.app.state.cancelled_runs,
            },
        )
        request.app.state.cancelled_runs.discard(prepared.run_id)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/chat/runs/{run_id}/cancel")
def cancel_run(request: Request, run_id: str, _current_user: CurrentUserDep) -> dict[str, bool]:
    """
    取消正在进行的流式生成。

    通过将 run_id 写入全局应用状态，使得正在输出的流能够检查到取消标志并提早中断。

    Args:
        request: FastAPI请求对象。
        run_id: 需要取消的任务ID。
        _current_user: 身份验证。

    Returns:
        dict: 确认已接收取消请求的响应。
    """
    request.app.state.cancelled_runs.add(run_id)
    return {"cancelled": True}


@router.get("/conversations/{conversation_id}")
def conversation_history(
    conversation_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ConversationResponse:
    """
    获取指定会话的历史记录。

    验证该会话是否属于当前用户，然后汇总消息以及相对应的行为轨迹（ai_trace）。

    Args:
        conversation_id: 目标会话ID。
        session: 数据库会话。
        current_user: 当前用户。

    Raises:
        AppError: 如果会话不存在或不属于该用户，返回 404。

    Returns:
        ConversationResponse: 包含整个对话树的视图对象。
    """
    conversation = session.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        raise AppError(404, "conversation_not_found", "会话不存在")
    trace_events = session.scalars(
        select(BehaviorEvent).where(
            BehaviorEvent.user_id == current_user.id,
            BehaviorEvent.event_type == "chat",
        )
    ).all()
    payloads_by_message_id = {
        event.payload.get("message_id"): event.payload
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
            ai_trace=payloads_by_message_id.get(message.id, {}).get("ai_trace", []),
            advisor_session_id=payloads_by_message_id.get(message.id, {}).get("advisor_session_id"),
            advisor_plan=payloads_by_message_id.get(message.id, {}).get("advisor_plan"),
        )
        for message in conversation.messages
    ]
    return ConversationResponse(
        id=conversation.id,
        knowledge_base_id=conversation.knowledge_base_id,
        knowledge_base_ids=link_ids(
            conversation.knowledge_base_links, conversation.knowledge_base_id
        ),
        summary=conversation.summary,
        messages=messages,
    )


@router.delete("/conversations/{conversation_id}", status_code=204)
def clear_conversation(
    conversation_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    """
    删除指定的会话，清空记录。

    Args:
        conversation_id: 要删除的会话ID。
        session: 数据库会话。
        current_user: 当前请求的用户。

    Raises:
        AppError: 当找不到属于该用户的会话时抛出。

    Returns:
        Response: 返回 204 No Content 代表成功。
    """
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
    """
    提交针对特定回答的用户反馈（顶、踩、纠错）。

    Args:
        payload: 包含评价结果的请求体。
        session: 数据库会话。
        current_user: 发起反馈的用户。

    Raises:
        AppError: 目标消息不存在或不是机器人的回复时抛出。

    Returns:
        FeedbackResponse: 反馈实体的最新状态。
    """
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
