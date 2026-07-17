from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


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


class HotTopicList(BaseModel):
    window: str
    items: list[HotTopic]


class UserProfileResponse(BaseModel):
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
