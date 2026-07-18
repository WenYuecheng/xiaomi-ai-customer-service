from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    knowledge_base_id: str
    conversation_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)
    stream: bool = False


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    chunk_id: str
    filename: str
    location: str
    snippet: str
    score: float
    source_url: str | None = None


class AiTraceStep(BaseModel):
    stage: Literal["understanding", "retrieval", "generation", "grounding"]
    status: Literal["running", "completed", "skipped", "degraded", "failed"]
    engine: str
    model: str
    duration_ms: int | None = None
    summary: str


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    run_id: str
    answer: str
    sources: list[SourceResponse]
    fallback: bool
    transfer_suggested: bool
    ai_trace: list[AiTraceStep] = Field(default_factory=list)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    fallback: bool
    created_at: datetime
    sources: list[SourceResponse] = Field(default_factory=list)
    ai_trace: list[AiTraceStep] = Field(default_factory=list)


class ConversationResponse(BaseModel):
    id: str
    knowledge_base_id: str
    summary: str | None
    messages: list[MessageResponse]


class FeedbackRequest(BaseModel):
    message_id: str
    rating: Literal["up", "down"]
    correction: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    message_id: str
    rating: str
    correction: str | None
