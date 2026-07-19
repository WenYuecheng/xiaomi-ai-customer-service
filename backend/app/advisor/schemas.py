"""
文件职责：
该文件负责定义AI产品选购顾问模块的输入输出数据模型和校验规则。

所属功能：
AI产品选购顾问模块的请求/响应协议(API Schemas)。

主要流程：
使用Pydantic定义数据模型，用于FastAPI的请求体解析、响应体序列化以及自动生成API文档。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.chat.schemas import AiTraceStep, SourceResponse


class AdvisorRequest(BaseModel):
    """
    负责定义发起首次选购顾问请求的数据结构。

    生命周期：
    在POST /advisor/sessions接口接收请求时创建，经过校验后传递给服务层生成会话和回复。

    属性：
    - knowledge_base_id: 关联的知识库ID
    - message: 用户的输入消息
    - mode: 选购模式(自动、对比、购买建议)
    - category: 产品类别
    - product_models: 用户关注的产品型号列表
    - budget_min: 最小预算
    - budget_max: 最大预算
    - priorities: 关注优先级列表
    - stream: 是否流式返回响应
    """

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
        """
        校验预算区间的合法性。

        Args:
            self: 当前实例对象。

        Returns:
            AdvisorRequest: 校验通过的实例。

        Raises:
            ValueError: 如果budget_min大于budget_max时抛出。
        """
        # 如果上下限都提供，则确保下限不大于上限
        if (
            self.budget_min is not None
            and self.budget_max is not None
            and self.budget_min > self.budget_max
        ):
            raise ValueError("budget_min must not exceed budget_max")
        return self


class AdvisorFollowUpRequest(BaseModel):
    """
    负责定义后续多轮追问的请求数据结构。

    生命周期：
    在POST /advisor/sessions/{session_id}/turns接口接收请求时创建。
    """

    message: str = Field(min_length=1, max_length=4000)
    budget_min: int | None = Field(default=None, ge=0, le=100000)
    budget_max: int | None = Field(default=None, ge=0, le=100000)
    priorities: list[str] | None = Field(default=None, max_length=5)
    stream: bool = False


class AdvisorPriceResponse(BaseModel):
    """
    负责封装产品价格相关的信息及其出处。
    """

    status: Literal["evidence", "unavailable"]
    display: str
    source_chunk_id: str | None = None
    captured_at: str | None = None


class AdvisorCandidateResponse(BaseModel):
    """
    负责表示向用户推荐的候选产品方案。
    """

    model: str
    fit_score: int
    highlights: list[str]
    tradeoffs: list[str]
    dimension_scores: dict[str, int]
    source_chunk_ids: list[str]
    price: AdvisorPriceResponse


class AdvisorComparisonRowResponse(BaseModel):
    """
    负责表示候选产品对比表格的一行数据。
    """

    dimension: str
    values: dict[str, str]


class AdvisorRecommendationResponse(BaseModel):
    """
    负责封装AI给出的最终推荐结论、理由和注意事项。
    """

    primary_model: str
    summary: str
    reasons: list[str]
    caveats: list[str]


class AdvisorPlanResponse(BaseModel):
    """
    负责汇总AI生成的完整选购方案结构。
    """

    title: str
    interpreted_need: str
    candidates: list[AdvisorCandidateResponse]
    comparison_rows: list[AdvisorComparisonRowResponse]
    recommendation: AdvisorRecommendationResponse
    follow_up_suggestions: list[str]


class AdvisorTurnResponse(BaseModel):
    """
    负责表示选购会话中单轮对话的完整响应数据。
    """

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
    """
    负责展示选购会话的简要信息。
    """

    id: str
    knowledge_base_id: str
    title: str
    category: str | None
    turn_count: int
    created_at: datetime
    updated_at: datetime


class AdvisorSessionResponse(AdvisorSessionSummary):
    """
    负责返回包含多轮对话详情的完整选购会话响应。
    """

    turns: list[AdvisorTurnResponse]


class AdvisorCreateResponse(BaseModel):
    """
    负责返回创建会话时的响应，包含会话摘要和首轮对话结果。
    """

    session: AdvisorSessionSummary
    turn: AdvisorTurnResponse


class AdvisorSessionList(BaseModel):
    """
    负责封装获取会话列表接口的响应，包含摘要列表和总数。
    """

    items: list[AdvisorSessionSummary]
    total: int
