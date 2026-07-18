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
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {payload}\n\n".encode()


def stream_events(events: Iterator[tuple[str, dict]]) -> Iterable[bytes]:
    for event, data in events:
        yield encode_event(event, data)


@router.post("/sessions", response_model=None)
def create_advisor_session(
    request: Request,
    payload: AdvisorRequest,
    db: SessionDep,
    current_user: CurrentUserDep,
) -> AdvisorCreateResponse | StreamingResponse:
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
    items = list_session_summaries(db, current_user)
    return AdvisorSessionList(items=items, total=len(items))


@router.get("/sessions/{session_id}")
def get_advisor_session(
    session_id: str,
    db: SessionDep,
    current_user: CurrentUserDep,
) -> AdvisorSessionResponse:
    return full_session_response(get_owned_session(db, session_id, current_user))


@router.post("/sessions/{session_id}/turns", response_model=None)
def create_advisor_follow_up(
    session_id: str,
    request: Request,
    payload: AdvisorFollowUpRequest,
    db: SessionDep,
    current_user: CurrentUserDep,
) -> AdvisorTurnResponse | StreamingResponse:
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
    item = get_owned_session(db, session_id, current_user)
    db.delete(item)
    db.commit()
    return Response(status_code=204)
