"""
文件职责：
该文件负责定义文档摄入（Ingestion）过程中的各种数据模型（Schemas），用于请求验证和响应序列化。

所属功能：
数据摄入服务（Ingestion Service） - 数据验证与序列化

主要流程：
定义了在文件上传、文档处理、分块处理以及异步任务状态查询等接口响应中使用的 Pydantic 模型类。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import DocumentStatus, JobStatus


class UploadResponse(BaseModel):
    """
    负责定义文件上传成功后的响应结构。

    该类包含文档上传后的核心标识信息和初始任务状态，供 API 返回给客户端，
    表明上传和初始化入库已完成。
    """

    document_id: str
    job_id: str
    status: JobStatus


class DocumentResponse(BaseModel):
    """
    负责定义单个文档详细信息的响应结构。

    通过启用 from_attributes=True，允许直接从 SQLAlchemy ORM 模型对象解析并构造数据。
    该类包含了文档元数据（如大小、类型、散列值）、处理状态以及分块配置等详细信息。
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    knowledge_base_id: str
    original_filename: str
    stored_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    status: DocumentStatus
    error_message: str | None
    chunk_size: int
    chunk_overlap: int
    source_url: str | None
    created_at: datetime


class DocumentList(BaseModel):
    """
    负责定义分页查询文档列表时的响应结构。
    包含了一个页面的所有文档记录，以及符合查询条件的总记录数。
    """

    items: list[DocumentResponse]
    total: int


class ChunkResponse(BaseModel):
    """
    负责定义文档分块（Chunk）的响应结构。

    包含了分块在原文档中的顺序（ordinal）、文本内容（text）、原位置（location）及提取出的产品模型信息。
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    ordinal: int
    text: str
    location: str
    product_models: list[str]


class ChunkList(BaseModel):
    """
    负责定义分页查询分块列表时的响应结构。
    包含分块数据数组和总记录数。
    """

    items: list[ChunkResponse]
    total: int


class JobResponse(BaseModel):
    """
    负责定义异步任务（Job）状态及详细信息的响应结构。

    主要用于追踪后台解析或索引任务的进度，包含当前处理状态、报错信息、重试次数及相关时间戳信息。
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    operation: str
    status: JobStatus
    stage: str
    error_message: str | None
    attempts: int
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class JobList(BaseModel):
    """
    负责定义分页查询异步任务列表时的响应结构。
    """

    items: list[JobResponse]
    total: int
