"""
文件职责：
定义后台运营与数据分析相关的输入与输出传输模型（DTO）。

所属功能：
运营分析与推荐 -> 视图模型/DTO。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MockOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_no: str
    product_name: str
    payment_status: str
    shipping_status: str
    logistics: list[str]
    is_mock: bool = True


class TicketCreate(BaseModel):
    conversation_id: str
    priority: Literal["low", "normal", "high", "urgent"] = "normal"


class TicketUpdate(BaseModel):
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    status: Literal["open", "in_progress", "resolved", "closed"] | None = None


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    category: str
    product_model: str | None
    summary: str
    attempted_solution: str | None
    priority: str
    status: str
    created_at: datetime


class HotTopic(BaseModel):
    term: str
    count: int
    score: float


class HotTopicHeatCell(BaseModel):
    date: str
    count: int


class HotTopicList(BaseModel):
    """热词排行及对应日期的热度分布（用于前端画热力图/折线图）"""

    window: str
    items: list[HotTopic]
    heatmap: list[HotTopicHeatCell] = Field(default_factory=list)


class UserProfileResponse(BaseModel):
    """
    用户画像响应。汇总该用户近期交流最多的产品、
    触发最多次的意图（如偏好知识咨询还是偏好查订单）及顶踩统计。
    """

    user_id: str
    product_preferences: list[str]
    intent_distribution: dict[str, int]
    feedback_summary: dict[str, int]
    event_count: int


class RecommendationItem(BaseModel):
    product_model: str
    score: float
    reason: str


class RecommendationList(BaseModel):
    """商品推荐列表。如果用户没有任何历史会话，cold_start 标志为 True。"""

    items: list[RecommendationItem]
    cold_start: bool


class TrainingRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version: str
    status: str
    precision_at_k: float | None
    recall_at_k: float | None
    artifact_filename: str | None
    failure_examples: list[dict]
    created_at: datetime
    finished_at: datetime | None
    target: Literal["balanced", "precision", "recall"] = "balanced"
    k: int = 3
    dataset_name: str = "unknown"
    sample_count: int = 0
    product_count: int = 0
    data_fingerprint: str = ""
    changed: bool = True
    metric_delta: dict[str, float | None] = Field(default_factory=dict)
    explanation: str = ""


class TrainingRequest(BaseModel):
    target: Literal["balanced", "precision", "recall"] = "balanced"


class ConversationLogItem(BaseModel):
    message_id: str
    conversation_id: str
    question: str
    answer: str
    intent: str | None
    fallback: bool
    latency_ms: int | None
    created_at: datetime


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    event_type: str
    payload: dict
    created_at: datetime


class FeedbackAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    message_id: str
    user_id: str
    rating: str
    correction: str | None
    created_at: datetime
