"""
文件职责：
定义智能问答交互及会话管理相关的输入与输出传输模型（DTO）。

所属功能：
智能问答 -> 视图模型/DTO。

主要流程：
通过 Pydantic 提供的 BaseModel 进行请求数据的验证（如长度、必填项），
并将数据库模型转换为响应到前端的 JSON 格式结构。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """
    前端向后端发起问答请求的结构。

    职责：定义并验证发起提问的入参格式。
    生命周期：在 /chat/completions 路由接收到请求时实例化并校验。

    属性:
        knowledge_base_id: 知识库 ID，必填。
        conversation_id: 会话 ID，若不传则表示开启新会话。
        message: 用户的问题文本。
        stream: 是否采用流式 SSE 返回。
    """

    knowledge_base_id: str | None = None
    knowledge_base_ids: list[str] | None = Field(default=None, min_length=1, max_length=5)
    conversation_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)
    stream: bool = False


class SourceResponse(BaseModel):
    """
    引用的知识库来源模型。

    职责：向前端展示模型回答时所引用的知识片段。
    生命周期：在回答生成或流式返回过程中被序列化。
    """

    model_config = ConfigDict(from_attributes=True)

    document_id: str
    chunk_id: str
    filename: str
    location: str
    snippet: str
    score: float
    source_url: str | None = None
    knowledge_base_id: str | None = None
    knowledge_base_name: str | None = None


class AiTraceStep(BaseModel):
    """
    流式传输中记录大模型思考与执行轨迹的数据结构。
    用于在前端界面上展示类似“检索知识库”、“阅读文档”、“思考中”的过程动画。

    职责：规范前端与后端的轨迹状态交互格式。
    生命周期：在整个回答准备过程（意图理解、检索、生成）中被持续产生并推送给前端。
    """

    stage: Literal["understanding", "retrieval", "reranking", "generation", "grounding"]
    status: Literal["running", "completed", "skipped", "degraded", "failed"]
    engine: str
    model: str
    duration_ms: int | None = None
    summary: str
    details: list[str] = Field(default_factory=list, max_length=3)


class ChatResponse(BaseModel):
    """
    非流式问答的整体响应模型。

    职责：定义一次完整问答交互的返回数据，包含所有核心元素（回答、来源、建议等）。
    """

    conversation_id: str
    knowledge_base_id: str
    knowledge_base_ids: list[str]
    message_id: str
    run_id: str
    answer: str
    sources: list[SourceResponse]
    fallback: bool
    transfer_suggested: bool
    ai_trace: list[AiTraceStep] = Field(default_factory=list)
    advisor_session_id: str | None = None
    advisor_plan: dict | None = None


class MessageResponse(BaseModel):
    """
    表示会话历史中单条消息的模型。

    职责：定义获取历史记录时的消息结构。
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    fallback: bool
    created_at: datetime
    sources: list[SourceResponse] = Field(default_factory=list)
    ai_trace: list[AiTraceStep] = Field(default_factory=list)
    advisor_session_id: str | None = None
    advisor_plan: dict | None = None


class ConversationResponse(BaseModel):
    """
    完整会话响应模型，包含多条消息。

    职责：为前端获取历史会话详情提供数据结构。
    """

    id: str
    knowledge_base_id: str
    knowledge_base_ids: list[str]
    summary: str | None
    messages: list[MessageResponse]


class FeedbackRequest(BaseModel):
    """
    用户评价反馈的请求体模型。

    职责：接收并验证用户提交的顶/踩与修正内容。
    """

    message_id: str
    rating: Literal["up", "down"]
    correction: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    """
    用户评价反馈的响应体模型。

    职责：返回评价保存成功后的实体状态。
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    message_id: str
    rating: str
    correction: str | None
