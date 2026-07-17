from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import AdminOrOperatorDep, CurrentUserDep
from app.core.errors import AppError
from app.db.base import SessionDep
from app.db.models import KnowledgeBase
from app.knowledge.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseList,
    KnowledgeBaseResponse,
)

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    session: SessionDep,
    current_user: AdminOrOperatorDep,
) -> KnowledgeBaseResponse:
    item = KnowledgeBase(
        name=payload.name.strip(),
        description=payload.description,
        embedding_model=payload.embedding_model,
        owner_id=current_user.id,
    )
    session.add(item)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise AppError(409, "knowledge_base_exists", "知识库名称已存在") from exc
    session.refresh(item)
    return KnowledgeBaseResponse.model_validate(item)


@router.get("")
def list_knowledge_bases(
    session: SessionDep,
    _current_user: CurrentUserDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[str | None, Query(alias="status", max_length=20)] = None,
) -> KnowledgeBaseList:
    statement = select(KnowledgeBase)
    count_statement = select(func.count()).select_from(KnowledgeBase)
    if q:
        condition = KnowledgeBase.name.ilike(f"%{q}%")
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    if status_filter:
        condition = KnowledgeBase.status == status_filter
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    items = list(session.scalars(statement.order_by(KnowledgeBase.created_at.desc())))
    return KnowledgeBaseList(
        items=[KnowledgeBaseResponse.model_validate(item) for item in items],
        total=session.scalar(count_statement) or 0,
    )

