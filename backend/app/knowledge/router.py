"""
文件职责：
定义知识库模块的 HTTP 路由接口，负责知识库的增删改查以及数据统计（分析与图谱）。

所属功能：
知识库管理 -> 路由层。

外部入口：
- GET `/api/v1/knowledge-bases` 列表
- POST `/api/v1/knowledge-bases` 创建
- GET/PATCH/DELETE `/api/v1/knowledge-bases/{id}` 详情、修改、删除
- GET `/api/v1/knowledge-bases/{id}/analytics` 统计数据
- GET `/api/v1/knowledge-bases/{id}/graph` 简易知识图谱数据
"""

from typing import Annotated

from fastapi import APIRouter, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminOrOperatorDep, CurrentUserDep
from app.core.errors import AppError
from app.db.base import SessionDep
from app.db.models import Document, DocumentChunk, KnowledgeBase
from app.knowledge.schemas import (
    CategoryCount,
    KnowledgeAnalyticsResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseList,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    KnowledgeGraphEdge,
    KnowledgeGraphNode,
    KnowledgeGraphResponse,
)

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge-bases"])


def require_knowledge_base(session: Session, knowledge_base_id: str) -> KnowledgeBase:
    """
    内部辅助函数：根据 ID 获取知识库对象。
    若不存在则抛出统一的 404 业务异常，减少各路由中的重复判空逻辑。
    """
    item = session.get(KnowledgeBase, knowledge_base_id)
    if not item:
        raise AppError(404, "knowledge_base_not_found", "知识库不存在")
    return item


def product_category(product: str) -> str:
    """
    内部辅助函数：根据提取到的产品型号字符串，通过关键字匹配粗略归类产品分类。
    """
    value = product.lower()
    if any(term in value for term in ("手环", "watch", "手表", "buds", "耳机")):
        return "智能穿戴"
    if any(term in value for term in ("p10", "x20", "扫地", "吸尘", "米家")):
        return "智能家居"
    if any(term in value for term in ("pad", "平板")):
        return "平板电脑"
    if any(term in value for term in ("xiaomi", "redmi", "小米")):
        return "手机"
    return "其他"


@router.get("/{knowledge_base_id}/analytics")
def knowledge_analytics(
    knowledge_base_id: str,
    session: SessionDep,
    _current_user: AdminOrOperatorDep,
) -> KnowledgeAnalyticsResponse:
    require_knowledge_base(session, knowledge_base_id)
    documents = list(
        session.scalars(select(Document).where(Document.knowledge_base_id == knowledge_base_id))
    )
    chunks = list(
        session.scalars(
            select(DocumentChunk).where(DocumentChunk.knowledge_base_id == knowledge_base_id)
        )
    )
    products = sorted({product for chunk in chunks for product in chunk.product_models})
    category_counts: dict[str, int] = {}
    for product in products:
        category = product_category(product)
        category_counts[category] = category_counts.get(category, 0) + 1
    sourced = sum(1 for document in documents if document.source_url)
    return KnowledgeAnalyticsResponse(
        document_count=len(documents),
        chunk_count=len(chunks),
        product_count=len(products),
        ready_count=sum(document.status.value == "ready" for document in documents),
        failed_count=sum(document.status.value == "failed" for document in documents),
        source_coverage=round(sourced / len(documents), 4) if documents else 0,
        categories=[
            CategoryCount(name=name, count=count) for name, count in sorted(category_counts.items())
        ],
    )


@router.get("/{knowledge_base_id}/graph")
def knowledge_graph(
    knowledge_base_id: str,
    session: SessionDep,
    _current_user: AdminOrOperatorDep,
) -> KnowledgeGraphResponse:
    knowledge_base = require_knowledge_base(session, knowledge_base_id)
    documents = list(
        session.scalars(select(Document).where(Document.knowledge_base_id == knowledge_base_id))
    )
    chunks = list(
        session.scalars(
            select(DocumentChunk).where(DocumentChunk.knowledge_base_id == knowledge_base_id)
        )
    )
    models_by_document: dict[str, set[str]] = {}
    for chunk in chunks:
        models_by_document.setdefault(chunk.document_id, set()).update(chunk.product_models)
    nodes = [
        KnowledgeGraphNode(
            id=f"kb:{knowledge_base.id}",
            label=knowledge_base.name,
            kind="knowledge_base",
            value=max(1, len(documents)),
        )
    ]
    edges: list[KnowledgeGraphEdge] = []
    categories: set[str] = set()
    products: set[str] = set()
    for document in documents:
        document_node = f"document:{document.id}"
        nodes.append(
            KnowledgeGraphNode(
                id=document_node,
                label=document.original_filename,
                kind="document",
                value=max(1, sum(chunk.document_id == document.id for chunk in chunks)),
            )
        )
        document_products = models_by_document.get(document.id, set())
        if not document_products:
            edges.append(
                KnowledgeGraphEdge(
                    source=f"kb:{knowledge_base.id}", target=document_node, relation="包含文档"
                )
            )
        for product in sorted(document_products):
            category = product_category(product)
            category_node = f"category:{category}"
            product_node = f"product:{product}"
            if category not in categories:
                categories.add(category)
                nodes.append(
                    KnowledgeGraphNode(
                        id=category_node, label=category, kind="category", category=category
                    )
                )
                edges.append(
                    KnowledgeGraphEdge(
                        source=f"kb:{knowledge_base.id}",
                        target=category_node,
                        relation="覆盖品类",
                    )
                )
            if product not in products:
                products.add(product)
                nodes.append(
                    KnowledgeGraphNode(
                        id=product_node,
                        label=product,
                        kind="product",
                        category=category,
                    )
                )
                edges.append(
                    KnowledgeGraphEdge(
                        source=category_node, target=product_node, relation="包含产品"
                    )
                )
            edges.append(
                KnowledgeGraphEdge(source=product_node, target=document_node, relation="来源文档")
            )
    return KnowledgeGraphResponse(nodes=nodes, edges=edges)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_knowledge_base(
    request: Request,
    payload: KnowledgeBaseCreate,
    session: SessionDep,
    current_user: AdminOrOperatorDep,
) -> KnowledgeBaseResponse:
    """
    功能：创建新知识库

    入口限制：
    仅 Admin 或 Operator 角色可调用。

    异常处理：
    利用数据库名称唯一约束（uq_knowledge_base_name），捕获 IntegrityError
    返回 409 冲突，而不是先 select 再 insert 导致并发问题。
    """
    item = KnowledgeBase(
        name=payload.name.strip(),
        description=payload.description,
        embedding_model=payload.embedding_model or request.app.state.settings.embedding_model,
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


@router.get("/{knowledge_base_id}")
def get_knowledge_base(
    knowledge_base_id: str, session: SessionDep, _current_user: CurrentUserDep
) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse.model_validate(require_knowledge_base(session, knowledge_base_id))


@router.patch("/{knowledge_base_id}")
def update_knowledge_base(
    knowledge_base_id: str,
    payload: KnowledgeBaseUpdate,
    session: SessionDep,
    _current_user: AdminOrOperatorDep,
) -> KnowledgeBaseResponse:
    item = require_knowledge_base(session, knowledge_base_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value.strip() if isinstance(value, str) else value)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise AppError(409, "knowledge_base_exists", "知识库名称已存在") from exc
    session.refresh(item)
    return KnowledgeBaseResponse.model_validate(item)


@router.delete("/{knowledge_base_id}", status_code=204)
def delete_knowledge_base(
    knowledge_base_id: str,
    session: SessionDep,
    _current_user: AdminOrOperatorDep,
) -> None:
    item = require_knowledge_base(session, knowledge_base_id)
    if item.documents:
        raise AppError(409, "knowledge_base_not_empty", "请先删除知识库中的文档")
    session.delete(item)
    session.commit()
