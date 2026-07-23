"""
文件职责：
定义系统内所有的持久化数据模型（实体表），并声明它们之间的关联关系。

所属功能：
核心基础设施 -> 数据库访问层 -> 数据模型定义。

设计说明：
统一使用 UUID(str) 作为主键；所有时间采用带时区的 DateTime（存储 UTC 时间）。
"""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    """获取当前时区感知的 UTC 时间，用于设置默认的创建与更新时间。"""
    return datetime.now(UTC)


class UserRole(StrEnum):
    """
    用户角色枚举：
    - admin: 管理员，拥有全站所有权限。
    - operator: 运营人员，管理知识库、文档与查看运营数据。
    - user: 普通 C 端用户，只能进行会话问答与提交反馈工单。
    """

    admin = "admin"
    operator = "operator"
    user = "user"


class User(Base):
    """
    数据模型：用户表 (users)
    业务含义：保存系统中所有注册的账号信息。
    数据来源：管理员初始化脚本（如 init-demo 命令）或注册接口。
    关联约束：一个用户可以拥有多个知识库（knowledge_bases）。
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # 登录使用的唯一标识符
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(40), default="")
    avatar_key: Mapped[str] = mapped_column(String(20), default="aurora")
    # 经过 bcrypt 加密后的密码散列值，绝不能返回给客户端
    password_hash: Mapped[str] = mapped_column(String(128))
    # 用户角色，决定其操作权限
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user)
    # 逻辑删除/封禁标识，为 False 时无法登录
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship(back_populates="owner")


class KnowledgeBase(Base):
    """
    数据模型：知识库表 (knowledge_bases)
    业务含义：用于对文档资料和向量检索集进行逻辑隔离分组。不同会话可绑定不同的知识库。
    关联约束：级联管理包含的所有文档 (documents)，若知识库删除，其下的所有文档记录一并删除。
    """

    __tablename__ = "knowledge_bases"
    __table_args__ = (UniqueConstraint("name", name="uq_knowledge_base_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # 知识库名称，全局唯一
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    # 状态字段：active, inactive 等
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    # 创建此知识库时选择的文本向量化（Embedding）模型标识，后续此库所有文档均用该模型解析
    embedding_model: Mapped[str] = mapped_column(String(100), default="mock-hash-embedding")
    # 创建人 ID
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    owner: Mapped[User] = relationship(back_populates="knowledge_bases")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="knowledge_base", cascade="all, delete-orphan"
    )


class JobStatus(StrEnum):
    """文档处理任务状态枚举"""

    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class DocumentStatus(StrEnum):
    """文档状态枚举"""

    queued = "queued"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Document(Base):
    """
    数据模型：文档表 (documents)
    业务含义：表示上传到知识库的一份原始文档资源。
    生命周期：创建(queued) -> 处理中(processing) -> 就绪(ready) 或 失败(failed)。
    """

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("knowledge_base_id", "sha256", name="uq_document_kb_sha256"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    knowledge_base_id: Mapped[str] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)
    media_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    # 通过文件散列值防止同一知识库内重复上传相同文件
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.queued, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    chunk_size: Mapped[int] = mapped_column(Integer, default=800)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=120)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    knowledge_base: Mapped[KnowledgeBase] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["ProcessingJob"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """
    数据模型：文档块 (document_chunks)
    业务含义：将原始文档拆分后，供向量数据库检索的文本片段。
    """

    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "ordinal", name="uq_chunk_ordinal"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    knowledge_base_id: Mapped[str] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    # 块在原文档中的排序号
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    # 该块的物理位置信息（例如页码等）
    location: Mapped[str] = mapped_column(String(200))
    product_models: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped[Document] = relationship(back_populates="chunks")


class ProcessingJob(Base):
    """
    数据模型：文档处理任务表 (processing_jobs)
    业务含义：用于异步跟踪文档向量化及分块等耗时任务的状态与重试。
    """

    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    operation: Mapped[str] = mapped_column(String(30), default="ingest")
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.queued, index=True)
    stage: Mapped[str] = mapped_column(String(50), default="queued")
    error_message: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    document: Mapped[Document] = relationship(back_populates="jobs")


class MessageRole(StrEnum):
    """消息角色：用户(user)或助手(assistant)"""

    user = "user"
    assistant = "assistant"


class Conversation(Base):
    """
    数据模型：会话表 (conversations)
    业务含义：用户与机器人之间的一次连贯的对话流程记录。
    """

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    knowledge_base_id: Mapped[str] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    summary: Mapped[str | None] = mapped_column(Text)
    summary_message_count: Mapped[int] = mapped_column(Integer, default=0)
    # 连续降级（未能匹配到有效信息而回退）的次数
    consecutive_fallbacks: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    knowledge_base_links: Mapped[list["ConversationKnowledgeBase"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationKnowledgeBase.ordinal",
    )


class ConversationKnowledgeBase(Base):
    """会话可检索知识库范围，ordinal 保留用户选择顺序。"""

    __tablename__ = "conversation_knowledge_bases"

    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), primary_key=True)
    knowledge_base_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_bases.id"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="knowledge_base_links")
    knowledge_base: Mapped[KnowledgeBase] = relationship()


class Message(Base):
    """
    数据模型：消息表 (messages)
    业务含义：一次会话中的单条消息实体。
    """

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole))
    content: Mapped[str] = mapped_column(Text)
    run_id: Mapped[str | None] = mapped_column(String(36), index=True)
    # 意图识别结果，例如"询问订单"、"查询保修"
    intent: Mapped[str | None] = mapped_column(String(30))
    # 是否是兜底回复（即 AI 没有足够的业务信息）
    fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    # 接口响应耗时
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    sources: Mapped[list["MessageSource"]] = relationship(
        back_populates="message", cascade="all, delete-orphan"
    )


class MessageSource(Base):
    """
    数据模型：消息参考来源表 (message_sources)
    业务含义：记录 AI 助手在回答时具体引用了哪些知识库文档片段及其相似度得分。
    """

    __tablename__ = "message_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("document_chunks.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(200))
    snippet: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float)

    message: Mapped[Message] = relationship(back_populates="sources")
    document: Mapped[Document] = relationship()

    @property
    def source_url(self) -> str | None:
        """获取原始文档的引用链接。"""
        return self.document.source_url

    @property
    def knowledge_base_id(self) -> str:
        return self.document.knowledge_base_id

    @property
    def knowledge_base_name(self) -> str:
        return self.document.knowledge_base.name


class FeedbackRating(StrEnum):
    """点赞或踩"""

    up = "up"
    down = "down"


class Feedback(Base):
    """
    数据模型：反馈表 (feedback)
    业务含义：用户对 AI 回复的点赞或点踩记录及纠错建议。
    """

    __tablename__ = "feedback"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_feedback_user_message"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    rating: Mapped[FeedbackRating] = mapped_column(Enum(FeedbackRating))
    correction: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class BehaviorEvent(Base):
    """
    数据模型：用户行为事件表 (behavior_events)
    业务含义：记录用户的操作日志以作统计与模型优化使用。
    """

    __tablename__ = "behavior_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, index=True
    )


class MockOrder(Base):
    """
    数据模型：模拟订单表 (mock_orders)
    业务含义：用于给客服提供测试用户的订单状态数据查询。
    """

    __tablename__ = "mock_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    order_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    product_name: Mapped[str] = mapped_column(String(200))
    payment_status: Mapped[str] = mapped_column(String(50))
    shipping_status: Mapped[str] = mapped_column(String(50))
    logistics: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Ticket(Base):
    """
    数据模型：工单表 (tickets)
    业务含义：当 AI 无法解决用户问题时，升级为人工工单处理。
    """

    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    category: Mapped[str] = mapped_column(String(50), default="customer_service")
    product_model: Mapped[str | None] = mapped_column(String(100))
    summary: Mapped[str] = mapped_column(Text)
    attempted_solution: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RecommendationTrainingRun(Base):
    """
    数据模型：推荐模型训练记录 (recommendation_training_runs)
    业务含义：记录推荐系统训练任务的状态及指标评估。
    """

    __tablename__ = "recommendation_training_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[str] = mapped_column(String(50), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    precision_at_k: Mapped[float | None] = mapped_column(Float)
    recall_at_k: Mapped[float | None] = mapped_column(Float)
    artifact_filename: Mapped[str | None] = mapped_column(String(255))
    failure_examples: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdvisorSession(Base):
    """
    数据模型：智能顾问会话 (advisor_sessions)
    业务含义：管理高级顾问业务流程（可能是针对特定产品的深层次指导）的对话框实例。
    """

    __tablename__ = "advisor_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    knowledge_base_id: Mapped[str] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    title: Mapped[str] = mapped_column(String(100))
    category: Mapped[str | None] = mapped_column(String(30), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    turns: Mapped[list["AdvisorTurn"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AdvisorTurn.sequence_no",
    )
    knowledge_base_links: Mapped[list["AdvisorSessionKnowledgeBase"]] = relationship(
        back_populates="advisor_session",
        cascade="all, delete-orphan",
        order_by="AdvisorSessionKnowledgeBase.ordinal",
    )


class AdvisorSessionKnowledgeBase(Base):
    """AI 选购会话创建时固定的多知识库范围。"""

    __tablename__ = "advisor_session_knowledge_bases"

    advisor_session_id: Mapped[str] = mapped_column(
        ForeignKey("advisor_sessions.id"), primary_key=True
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_bases.id"), primary_key=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)

    advisor_session: Mapped[AdvisorSession] = relationship(back_populates="knowledge_base_links")
    knowledge_base: Mapped[KnowledgeBase] = relationship()


class AdvisorTurn(Base):
    """
    数据模型：智能顾问会话回合 (advisor_turns)
    业务含义：记录顾问模式下每次用户提问以及 AI 决策过程的结构化输出（计划、来源、轨迹）。
    """

    __tablename__ = "advisor_turns"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence_no", name="uq_advisor_turn_sequence"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("advisor_sessions.id"), index=True)
    message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"), index=True)
    sequence_no: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)
    # AI 提取的用户需求
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    # AI 规划的解决步骤
    plan: Mapped[dict] = mapped_column(JSON, default=dict)
    # 引用的资料
    sources: Mapped[list[dict]] = mapped_column(JSON, default=list)
    # 思考链路追溯
    ai_trace: Mapped[list[dict]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="completed", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[AdvisorSession] = relationship(back_populates="turns")
