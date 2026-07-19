"""
文件职责：
定义知识库模块的 HTTP 路由接口，负责知识库的增删改查以及数据统计（分析与图谱）。

所属功能：
知识库管理服务（Knowledge Base Service） -> 路由层。

主要流程：
定义了相关的 RESTful API 端点：
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

    主要职责：
    通过数据库会话获取特定的知识库实例，若不存在则抛出统一的 404 业务异常，
    以此减少各路由中的重复判空逻辑，保持路由代码的简洁。

    Args:
        session: 当前的数据库会话。
        knowledge_base_id: 需要查询的知识库 ID。

    Returns:
        找到的 KnowledgeBase 数据库实例。

    Raises:
        AppError: 当查询不到对应的知识库时，抛出 404 异常。
    """
    item = session.get(KnowledgeBase, knowledge_base_id)
    if not item:
        raise AppError(404, "knowledge_base_not_found", "知识库不存在")
    return item


def product_category(product: str) -> str:
    """
    内部辅助函数：根据提取到的产品型号字符串，通过关键字匹配粗略归类产品分类。

    主要职责：
    用于生成知识分析与知识图谱展示时的节点归属类别（如“智能穿戴”、“手机”等）。

    Args:
        product: 产品型号字符串（如 "xiaomi watch s3"）。

    Returns:
        对应的中文产品类别（str）。
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
    """
    获取指定知识库的数据分析看板指标。

    主要职责：
    查询统计当前知识库下的文档数量、片段总数、涵盖的设备产品线以及各类别的统计分布，
    返回供前端可视化图表使用的核心数据。

    Args:
        knowledge_base_id: 知识库的 UUID。
        session: 依赖注入的数据库会话。
        _current_user: 权限校验依赖，需 Admin 或 Operator。

    Returns:
        KnowledgeAnalyticsResponse: 包含汇总统计信息的响应对象。
    """
    require_knowledge_base(session, knowledge_base_id)
    # 获取所有的文档及分块
    documents = list(
        session.scalars(select(Document).where(Document.knowledge_base_id == knowledge_base_id))
    )
    chunks = list(
        session.scalars(
            select(DocumentChunk).where(DocumentChunk.knowledge_base_id == knowledge_base_id)
        )
    )

    # 从切片中提取所有独特的产品模型并排序
    products = sorted({product for chunk in chunks for product in chunk.product_models})
    category_counts: dict[str, int] = {}

    # 按照业务逻辑统计各种设备类型的数量分布
    for product in products:
        category = product_category(product)
        category_counts[category] = category_counts.get(category, 0) + 1

    # 计算带有来源 URL 的文档占比
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
    """
    获取指定知识库的简易知识图谱数据。

    主要职责：
    提取该知识库下的文档、产品、品类之间的关联关系（节点和边），
    供前端知识图谱组件（如 echarts / G6）渲染层级或网状可视化视图。

    Args:
        knowledge_base_id: 知识库的 UUID。
        session: 依赖注入的数据库会话。
        _current_user: 权限校验依赖，需 Admin 或 Operator。

    Returns:
        KnowledgeGraphResponse: 包含 nodes 和 edges 列表的对象。
    """
    knowledge_base = require_knowledge_base(session, knowledge_base_id)
    documents = list(
        session.scalars(select(Document).where(Document.knowledge_base_id == knowledge_base_id))
    )
    chunks = list(
        session.scalars(
            select(DocumentChunk).where(DocumentChunk.knowledge_base_id == knowledge_base_id)
        )
    )

    # 构建从 文档 ID 到 其涵盖产品列表的映射
    models_by_document: dict[str, set[str]] = {}
    for chunk in chunks:
        models_by_document.setdefault(chunk.document_id, set()).update(chunk.product_models)

    # 根节点：当前知识库本身
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

    # 遍历处理各层级实体与关联线
    for document in documents:
        document_node = f"document:{document.id}"
        # 添加文档节点，权重由相关切片数量决定
        nodes.append(
            KnowledgeGraphNode(
                id=document_node,
                label=document.original_filename,
                kind="document",
                value=max(1, sum(chunk.document_id == document.id for chunk in chunks)),
            )
        )

        document_products = models_by_document.get(document.id, set())
        # 如果该文档未提取出任何实体，直接将其与知识库相连
        if not document_products:
            edges.append(
                KnowledgeGraphEdge(
                    source=f"kb:{knowledge_base.id}", target=document_node, relation="包含文档"
                )
            )

        # 根据提取出的产品，连线 `知识库 -> 分类 -> 产品 -> 文档`
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
            # 连接具体产品与其实体出处的文档
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

    主要职责：
    接收用户参数实例化 `KnowledgeBase` 并在数据库中落表。

    入口限制：
    仅 Admin 或 Operator 角色可调用。

    异常处理：
    利用数据库名称唯一约束（uq_knowledge_base_name），捕获 `IntegrityError`
    返回 409 冲突，避免了先 select 再 insert 可能导致的并发脏写问题。
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
