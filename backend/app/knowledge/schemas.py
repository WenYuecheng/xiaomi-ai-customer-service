from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    embedding_model: str | None = Field(default=None, max_length=100)


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    status: str | None = Field(default=None, pattern="^(active|archived)$")


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    status: str
    embedding_model: str
    owner_id: str
    created_at: datetime


class KnowledgeBaseList(BaseModel):
    items: list[KnowledgeBaseResponse]
    total: int


class CategoryCount(BaseModel):
    name: str
    count: int


class KnowledgeAnalyticsResponse(BaseModel):
    document_count: int
    chunk_count: int
    product_count: int
    ready_count: int
    failed_count: int
    source_coverage: float
    categories: list[CategoryCount]


class KnowledgeGraphNode(BaseModel):
    id: str
    label: str
    kind: str
    value: int = 1
    category: str | None = None


class KnowledgeGraphEdge(BaseModel):
    source: str
    target: str
    relation: str


class KnowledgeGraphResponse(BaseModel):
    nodes: list[KnowledgeGraphNode]
    edges: list[KnowledgeGraphEdge]
