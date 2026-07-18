from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.chat.schemas import AiTraceStep, SourceResponse


class AdvisorRequest(BaseModel):
    knowledge_base_id: str
    message: str = Field(min_length=1, max_length=4000)
    mode: Literal["auto", "comparison", "purchase_advice"] = "auto"
    category: Literal["phone", "tablet", "wearable", "robot_vacuum"] | None = None
    product_models: list[str] = Field(default_factory=list, max_length=4)
    budget_min: int | None = Field(default=None, ge=0, le=100000)
    budget_max: int | None = Field(default=None, ge=0, le=100000)
    priorities: list[str] = Field(default_factory=list, max_length=5)
    stream: bool = False

    @model_validator(mode="after")
    def validate_budget(self) -> "AdvisorRequest":
        if (
            self.budget_min is not None
            and self.budget_max is not None
            and self.budget_min > self.budget_max
        ):
            raise ValueError("budget_min must not exceed budget_max")
        return self


class AdvisorFollowUpRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    budget_min: int | None = Field(default=None, ge=0, le=100000)
    budget_max: int | None = Field(default=None, ge=0, le=100000)
    priorities: list[str] | None = Field(default=None, max_length=5)
    stream: bool = False


class AdvisorPriceResponse(BaseModel):
    status: Literal["evidence", "unavailable"]
    display: str
    source_chunk_id: str | None = None
    captured_at: str | None = None


class AdvisorCandidateResponse(BaseModel):
    model: str
    fit_score: int
    highlights: list[str]
    tradeoffs: list[str]
    dimension_scores: dict[str, int]
    source_chunk_ids: list[str]
    price: AdvisorPriceResponse


class AdvisorComparisonRowResponse(BaseModel):
    dimension: str
    values: dict[str, str]


class AdvisorRecommendationResponse(BaseModel):
    primary_model: str
    summary: str
    reasons: list[str]
    caveats: list[str]


class AdvisorPlanResponse(BaseModel):
    title: str
    interpreted_need: str
    candidates: list[AdvisorCandidateResponse]
    comparison_rows: list[AdvisorComparisonRowResponse]
    recommendation: AdvisorRecommendationResponse
    follow_up_suggestions: list[str]


class AdvisorTurnResponse(BaseModel):
    id: str
    sequence_no: int
    question: str
    requirements: dict
    plan: AdvisorPlanResponse | None
    sources: list[SourceResponse]
    ai_trace: list[AiTraceStep]
    status: str
    created_at: datetime


class AdvisorSessionSummary(BaseModel):
    id: str
    knowledge_base_id: str
    title: str
    category: str | None
    turn_count: int
    created_at: datetime
    updated_at: datetime


class AdvisorSessionResponse(AdvisorSessionSummary):
    turns: list[AdvisorTurnResponse]


class AdvisorCreateResponse(BaseModel):
    session: AdvisorSessionSummary
    turn: AdvisorTurnResponse


class AdvisorSessionList(BaseModel):
    items: list[AdvisorSessionSummary]
    total: int
