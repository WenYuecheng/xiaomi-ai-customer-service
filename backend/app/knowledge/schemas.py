"""
文件职责：
该文件负责定义知识库（Knowledge Base）相关业务过程中的请求体与响应体的数据模型。

所属功能：
知识库管理服务（Knowledge Base Service） - 数据验证与序列化

主要流程：
定义了创建、更新知识库的入参验证模型，以及返回知识库详情、列表、数据看板分析和知识图谱相关结构的响应模型。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseCreate(BaseModel):
    """
    负责定义创建新知识库时的请求体结构。

    提供对输入参数的长度限制校验。
    """

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    embedding_model: str | None = Field(default=None, max_length=100)


class KnowledgeBaseUpdate(BaseModel):
    """
    负责定义更新知识库信息时的请求体结构。

    使用可选字段（Optional/None）允许部分更新，同时对状态字段进行正则约束
    （active 或 archived）。
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(active|archived)$")


class KnowledgeBaseResponse(BaseModel):
    """
    负责定义查询单条知识库详情的响应结构。

    启用 ORM 模型转化能力。包含所有核心的知识库配置和状态数据。
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    status: str
    embedding_model: str
    owner_id: str
    created_at: datetime


class KnowledgeBaseList(BaseModel):
    """
    负责定义知识库列表查询的响应结构。
    包含当前页面的知识库项和总数量。
    """

    items: list[KnowledgeBaseResponse]
    total: int


class CategoryCount(BaseModel):
    """
    用于统计数据分析模型中的子模型。
    表示某个维度的分类名称及其对应的统计数量。
    """

    name: str
    count: int


class KnowledgeAnalyticsResponse(BaseModel):
    """
    负责定义知识库分析看板的响应结构。

    包含了文档总量、分块总量、相关产品数等全局统计数据，以及按特定维度的分类统计列表。
    """

    document_count: int
    chunk_count: int
    product_count: int
    ready_count: int
    failed_count: int
    source_coverage: float
    categories: list[CategoryCount]


class KnowledgeGraphNode(BaseModel):
    """
    负责定义知识图谱中单个节点的数据结构。

    包含节点标识、标签、类型以及可选的权重值（value）和归属分类。
    """

    id: str
    label: str
    kind: str
    value: int = 1
    category: str | None = None


class KnowledgeGraphEdge(BaseModel):
    """
    负责定义知识图谱中节点间关联边的数据结构。

    包含起始节点（source）、目标节点（target）以及对应的关系类型。
    """

    source: str
    target: str
    relation: str


class KnowledgeGraphResponse(BaseModel):
    """
    负责定义完整的知识图谱响应结构。

    返回一组节点列表和连接这些节点的边列表，用于前端可视化渲染。
    """

    nodes: list[KnowledgeGraphNode]
    edges: list[KnowledgeGraphEdge]
