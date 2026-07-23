"""多知识库选择的兼容、校验与持久化辅助函数。"""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import KnowledgeBase


def resolve_knowledge_base_ids(
    knowledge_base_id: str | None,
    knowledge_base_ids: Sequence[str] | None,
) -> list[str]:
    """合并新旧协议，并在两者表达不同范围时明确拒绝。"""
    selected = list(dict.fromkeys(knowledge_base_ids or []))
    if knowledge_base_id and selected and (len(selected) != 1 or selected[0] != knowledge_base_id):
        raise AppError(
            422,
            "knowledge_base_selection_conflict",
            "knowledge_base_id 与 knowledge_base_ids 冲突",
        )
    if not selected and knowledge_base_id:
        selected = [knowledge_base_id]
    if not selected:
        raise AppError(422, "knowledge_base_selection_required", "请至少选择一个知识库")
    if len(selected) > 5:
        raise AppError(422, "too_many_knowledge_bases", "最多同时选择 5 个知识库")
    return selected


def require_active_knowledge_bases(
    session: Session, knowledge_base_ids: Sequence[str]
) -> list[KnowledgeBase]:
    """按请求顺序返回有效知识库，禁止查询不存在或停用的库。"""
    result: list[KnowledgeBase] = []
    for knowledge_base_id in knowledge_base_ids:
        item = session.get(KnowledgeBase, knowledge_base_id)
        if not item:
            raise AppError(404, "knowledge_base_not_found", "知识库不存在")
        if item.status != "active":
            raise AppError(409, "knowledge_base_inactive", f"知识库“{item.name}”已停用")
        result.append(item)
    return result


def link_ids(links: Sequence[object], legacy_id: str) -> list[str]:
    """兼容迁移前/测试直接创建的旧记录。"""
    ids = [link.knowledge_base_id for link in links]  # type: ignore[attr-defined]
    return ids or [legacy_id]
