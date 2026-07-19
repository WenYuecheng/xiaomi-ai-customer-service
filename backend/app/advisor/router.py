"""
文件职责：
该文件负责定义AI产品选购顾问模块的所有RESTful API路由(HTTP endpoints)。

所属功能：
AI产品选购顾问模块的API层。

主要流程：
接收来自客户端的HTTP请求，处理鉴权与依赖注入，调用业务逻辑层(service.py)处理核心逻辑，并将结果封装后响应给客户端。
"""

import json
from collections.abc import Iterable, Iterator

from fastapi import APIRouter, Request, Response
from starlette.responses import StreamingResponse

from app.advisor.schemas import (
    AdvisorCreateResponse,
    AdvisorFollowUpRequest,
    AdvisorRequest,
    AdvisorSessionList,
    AdvisorSessionResponse,
    AdvisorTurnResponse,
)
from app.advisor.service import (
    advisor_events,
    consume_advisor_events,
    create_response,
    create_session_record,
    full_session_response,
    get_owned_session,
    list_session_summaries,
    turn_response,
    validate_sensitive_input,
)
from app.auth.dependencies import CurrentUserDep
from app.db.base import SessionDep

router = APIRouter(prefix="/advisor", tags=["AI advisor"])


def encode_event(event: str, data: dict) -> bytes:
    """
    负责将事件数据编码为Server-Sent Events (SSE)格式。

    Args:
        event (str): 事件名称。
        data (dict): 事件携带的数据载荷。

    Returns:
        bytes: 编码后的SSE格式字节流。
    """
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n".encode()


def stream_events(events: Iterator[tuple[str, dict]]) -> Iterable[bytes]:
    """
    负责将生成的事件流持续转化为SSE字节流序列。

    Args:
        events (Iterator[tuple[str, dict]]): 生成(event, data)元组的迭代器。

    Yields:
        bytes: 编码后的SSE格式字节流。
    """
    for event, data in events:
        yield encode_event(event, data)


@router.post("/sessions", response_model=None)
def create_advisor_session(
    request: Request,
    payload: AdvisorRequest,
    db: SessionDep,
    current_user: CurrentUserDep,
) -> AdvisorCreateResponse | StreamingResponse:
    """
    负责创建新的产品选购顾问会话。

    Args:
        request (Request): FastAPI的请求对象。
        payload (AdvisorRequest): 客户端传入的创建会话请求载荷。
        db (SessionDep): 数据库会话依赖。
        current_user (CurrentUserDep): 当前已认证的用户对象。

    Returns:
        AdvisorCreateResponse | StreamingResponse:
            如果不是流式请求，则返回同步处理完成的完整响应；如果是流式请求，则返回SSE事件流。

    Raises:
        AppError: 如果知识库不存在或敏感词校验未通过时抛出。
    """
    validate_sensitive_input(db, request.app.state.settings, current_user, payload.message)
    item = create_session_record(
        db,
        current_user,
        payload.knowledge_base_id,
        payload.category,
    )
    overrides = payload.model_dump(exclude={"knowledge_base_id", "message", "stream"})
    events = advisor_events(
        db,
        request.app.state.settings,
        request.app.state.worker.vector_store,
        current_user,
        item,
        payload.message,
        overrides,
    )
    if payload.stream:
        return StreamingResponse(stream_events(events), media_type="text/event-stream")
    consume_advisor_events(events)
    return create_response(item)


@router.get("/sessions")
def list_advisor_sessions(db: SessionDep, current_user: CurrentUserDep) -> AdvisorSessionList:
    """
    负责获取当前用户所有的选购会话摘要列表。

    Args:
        db (SessionDep): 数据库会话依赖。
        current_user (CurrentUserDep): 当前已认证的用户对象。

    Returns:
        AdvisorSessionList: 包含会话摘要列表及总数的响应对象。
    """
    items = list_session_summaries(db, current_user)
    return AdvisorSessionList(items=items, total=len(items))


@router.get("/sessions/{session_id}")
def get_advisor_session(
    session_id: str,
    db: SessionDep,
    current_user: CurrentUserDep,
) -> AdvisorSessionResponse:
    """
    负责获取指定选购会话的详情及所有对话记录。

    Args:
        session_id (str): 会话ID。
        db (SessionDep): 数据库会话依赖。
        current_user (CurrentUserDep): 当前已认证的用户对象。

    Returns:
        AdvisorSessionResponse: 包含该会话完整对话轮次数据的详情。

    Raises:
        AppError: 如果会话不存在或者不属于当前用户时抛出。
    """
    return full_session_response(get_owned_session(db, session_id, current_user))


@router.post("/sessions/{session_id}/turns", response_model=None)
def create_advisor_follow_up(
    session_id: str,
    request: Request,
    payload: AdvisorFollowUpRequest,
    db: SessionDep,
    current_user: CurrentUserDep,
) -> AdvisorTurnResponse | StreamingResponse:
    """
    负责处理用户在已有选购会话中的追问或后续补充需求。

    Args:
        session_id (str): 会话ID。
        request (Request): FastAPI的请求对象。
        payload (AdvisorFollowUpRequest): 客户端传入的追问请求载荷。
        db (SessionDep): 数据库会话依赖。
        current_user (CurrentUserDep): 当前已认证的用户对象。

    Returns:
        AdvisorTurnResponse | StreamingResponse:
            非流式则返回单轮对话结果；流式则返回SSE事件流。

    Raises:
        AppError: 如果会话不存在、不属于当前用户或敏感词校验未通过时抛出。
    """
    validate_sensitive_input(db, request.app.state.settings, current_user, payload.message)
    item = get_owned_session(db, session_id, current_user)
    overrides = payload.model_dump(exclude={"message", "stream"})
    events = advisor_events(
        db,
        request.app.state.settings,
        request.app.state.worker.vector_store,
        current_user,
        item,
        payload.message,
        overrides,
    )
    if payload.stream:
        return StreamingResponse(stream_events(events), media_type="text/event-stream")
    consume_advisor_events(events)
    return turn_response(item.turns[-1])


@router.delete("/sessions/{session_id}", status_code=204)
def delete_advisor_session(
    session_id: str,
    db: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    """
    负责删除指定的选购会话。

    Args:
        session_id (str): 会话ID。
        db (SessionDep): 数据库会话依赖。
        current_user (CurrentUserDep): 当前已认证的用户对象。

    Returns:
        Response: 删除成功返回204状态码。

    Raises:
        AppError: 如果会话不存在或者不属于当前用户时抛出。
    """
    item = get_owned_session(db, session_id, current_user)
    db.delete(item)
    db.commit()
    return Response(status_code=204)
