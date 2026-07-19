"""
文件职责：
定义文档接入模块的 HTTP 路由。处理文件上传、文档记录查询、分块内容查询、解析任务查询及重试等操作。

所属功能：
数据摄入服务（Ingestion Service） -> 路由层。

主要流程：
处理客户端发起的各类 HTTP RESTful 请求：
- POST `/api/v1/documents/upload` 上传文件并提交解析任务
- GET `/api/v1/documents` 及详情
- GET `/api/v1/documents/{id}/chunks` 查询切片
- GET `/api/v1/jobs` 及详情
- POST `/api/v1/jobs/{id}/retry` 任务重试
- DELETE `/api/v1/documents/{id}` 删除文档
"""

import hashlib
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, status
from pydantic import AnyHttpUrl
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import AdminOrOperatorDep
from app.core.errors import AppError
from app.db.base import SessionDep
from app.db.models import (
    Document,
    DocumentChunk,
    DocumentStatus,
    KnowledgeBase,
    ProcessingJob,
)
from app.ingestion.schemas import (
    ChunkList,
    ChunkResponse,
    DocumentList,
    DocumentResponse,
    JobList,
    JobResponse,
    UploadResponse,
)

router = APIRouter(tags=["documents"])
ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}


def safe_original_name(filename: str | None) -> str:
    """
    内部安全机制：防范目录遍历攻击（Directory Traversal）。

    主要职责：
    剥离路径前缀，仅提取并保留安全的文件名部分。

    Args:
        filename: 客户端上传时声明的原始文件名。

    Returns:
        清理后的安全文件名字符串。

    Raises:
        AppError: 当提取后文件名为空或超长时抛出 400 异常。
    """
    name = Path((filename or "").replace("\\", "/")).name.strip()
    if not name or len(name) > 255:
        raise AppError(400, "invalid_filename", "文件名无效")
    return name


def validate_signature(suffix: str, content: bytes) -> None:
    """
    内部安全校验：通过文件魔数（Magic Number）或试解码验证内容，防止伪造后缀名上传恶意文件。
    """
    valid = True
    if suffix == ".pdf":
        valid = content.startswith(b"%PDF-")
    elif suffix == ".docx":
        valid = content.startswith(b"PK\x03\x04")
    elif suffix in {".txt", ".md"}:
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError:
            valid = False
    if not valid:
        raise AppError(415, "invalid_file_signature", "文件内容与声明格式不匹配")


@router.post("/documents/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    request: Request,
    session: SessionDep,
    _current_user: AdminOrOperatorDep,
    knowledge_base_id: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    chunk_size: Annotated[int | None, Form(ge=200, le=4000)] = None,
    chunk_overlap: Annotated[int | None, Form(ge=0, le=800)] = None,
    source_url: Annotated[AnyHttpUrl | None, Form()] = None,
) -> UploadResponse:
    """
    接收用户上传的新文档并提交异步解析任务入库。

    功能归属：
    文档接入生命周期的起点。

    执行链：
    1. 接收文件并进行参数、尺寸、格式和内容签名安全校验。
    2. 将文件实体存储于本地指定路径（`data/uploads`）。
    3. 生成 `Document` 和 `ProcessingJob` 数据库记录，初始状态为 queued。
    4. 通知后台异步任务守护线程 `worker.notify()`，唤醒消费。

    Args:
        request: FastAPI 请求对象。
        session: 依赖注入的数据库会话。
        _current_user: 权限校验，要求管理员或操作员权限。
        knowledge_base_id: 关联的知识库 UUID（表单参数）。
        file: 客户端上传的多部分文件。
        chunk_size: 文档解析时的切块大小，默认从全局配置读取。
        chunk_overlap: 切块间的重叠字符数。
        source_url: 可选的外部引用链接。

    Returns:
        UploadResponse: 包含创建的文档及任务 ID、状态的响应对象。

    Raises:
        AppError: HTTP 层面上抛出 404/415/413/422/409，
                  分别对应未找到/类型不支持/过大/参数错误/防重冲突。
    """
    settings = request.app.state.settings
    knowledge_base = session.get(KnowledgeBase, knowledge_base_id)
    if not knowledge_base:
        raise AppError(404, "knowledge_base_not_found", "知识库不存在")

    # 安全提取和校验
    name = safe_original_name(file.filename)
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise AppError(415, "unsupported_file_type", "仅支持 PDF、DOCX、TXT 和 MD")

    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise AppError(413, "file_too_large", "文件超过大小限制")
    if not content:
        raise AppError(400, "empty_file", "文件内容为空")

    # 执行魔数安全校验
    validate_signature(suffix, content)

    actual_chunk_size = chunk_size or settings.chunk_size
    actual_overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap
    if actual_overlap >= actual_chunk_size:
        raise AppError(422, "invalid_chunk_config", "chunk_overlap 必须小于 chunk_size")

    stored_name = f"{uuid4()}{suffix}"
    target = (settings.upload_dir / stored_name).resolve()
    base = settings.upload_dir.resolve()

    # 防止因文件系统特性导致的越权写入
    if target.parent != base:
        raise AppError(400, "invalid_filename", "文件存储路径无效")

    # 物理落盘
    target.write_bytes(content)

    document = Document(
        knowledge_base_id=knowledge_base_id,
        original_filename=name,
        stored_filename=stored_name,
        media_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        chunk_size=actual_chunk_size,
        chunk_overlap=actual_overlap,
        source_url=str(source_url) if source_url else None,
    )
    job = ProcessingJob(document=document)
    session.add_all([document, job])

    try:
        session.commit()
    except IntegrityError as exc:
        # 并发环境下防重复散列，若发生约束冲突则回滚并清理物理文件
        session.rollback()
        target.unlink(missing_ok=True)
        raise AppError(409, "document_exists", "该知识库已存在相同文件") from exc

    # 成功落库后，通知守护线程干活
    request.app.state.worker.notify()
    return UploadResponse(document_id=document.id, job_id=job.id, status=job.status)


@router.get("/documents/{document_id}")
def get_document(
    document_id: str, session: SessionDep, _current_user: AdminOrOperatorDep
) -> DocumentResponse:
    document = session.get(Document, document_id)
    if not document:
        raise AppError(404, "document_not_found", "文档不存在")
    return DocumentResponse.model_validate(document)


@router.get("/documents")
def list_documents(
    session: SessionDep,
    _current_user: AdminOrOperatorDep,
    knowledge_base_id: str | None = None,
) -> DocumentList:
    statement = select(Document)
    count_statement = select(func.count()).select_from(Document)
    if knowledge_base_id:
        statement = statement.where(Document.knowledge_base_id == knowledge_base_id)
        count_statement = count_statement.where(Document.knowledge_base_id == knowledge_base_id)
    documents = list(session.scalars(statement.order_by(Document.created_at.desc())))
    return DocumentList(
        items=[DocumentResponse.model_validate(document) for document in documents],
        total=session.scalar(count_statement) or 0,
    )


@router.get("/documents/{document_id}/chunks")
def list_chunks(
    document_id: str, session: SessionDep, _current_user: AdminOrOperatorDep
) -> ChunkList:
    if not session.get(Document, document_id):
        raise AppError(404, "document_not_found", "文档不存在")
    chunks = list(
        session.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.ordinal)
        )
    )
    return ChunkList(
        items=[ChunkResponse.model_validate(chunk) for chunk in chunks], total=len(chunks)
    )


@router.get("/jobs/{job_id}")
def get_job(job_id: str, session: SessionDep, _current_user: AdminOrOperatorDep) -> JobResponse:
    job = session.get(ProcessingJob, job_id)
    if not job:
        raise AppError(404, "job_not_found", "处理任务不存在")
    return JobResponse.model_validate(job)


@router.get("/jobs")
def list_jobs(
    session: SessionDep,
    _current_user: AdminOrOperatorDep,
    document_id: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status", max_length=20)] = None,
) -> JobList:
    statement = select(ProcessingJob)
    count_statement = select(func.count()).select_from(ProcessingJob)
    if document_id:
        statement = statement.where(ProcessingJob.document_id == document_id)
        count_statement = count_statement.where(ProcessingJob.document_id == document_id)
    if status_filter:
        statement = statement.where(ProcessingJob.status == status_filter)
        count_statement = count_statement.where(ProcessingJob.status == status_filter)
    jobs = list(session.scalars(statement.order_by(ProcessingJob.created_at.desc())))
    return JobList(
        items=[JobResponse.model_validate(job) for job in jobs],
        total=session.scalar(count_statement) or 0,
    )


def queue_document_job(
    request: Request, session: Session, document: Document, operation: str
) -> UploadResponse:
    if document.status.value == "processing":
        raise AppError(409, "document_busy", "文档正在处理中")
    job = ProcessingJob(document_id=document.id, operation=operation)
    document.status = DocumentStatus.queued
    document.error_message = None
    session.add(job)
    session.commit()
    request.app.state.worker.notify()
    return UploadResponse(document_id=document.id, job_id=job.id, status=job.status)


@router.post("/documents/{document_id}/reindex", status_code=202)
def reindex_document(
    request: Request,
    document_id: str,
    session: SessionDep,
    _current_user: AdminOrOperatorDep,
) -> UploadResponse:
    document = session.get(Document, document_id)
    if not document:
        raise AppError(404, "document_not_found", "文档不存在")
    return queue_document_job(request, session, document, "reindex")


@router.post("/jobs/{job_id}/retry", status_code=202)
def retry_job(
    request: Request,
    job_id: str,
    session: SessionDep,
    _current_user: AdminOrOperatorDep,
) -> UploadResponse:
    job = session.get(ProcessingJob, job_id)
    if not job:
        raise AppError(404, "job_not_found", "处理任务不存在")
    if job.status.value != "failed":
        raise AppError(409, "job_not_failed", "仅失败任务可以重试")
    return queue_document_job(request, session, job.document, f"retry:{job.operation}")


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    request: Request,
    document_id: str,
    session: SessionDep,
    _current_user: AdminOrOperatorDep,
) -> None:
    """
    删除指定的文档。

    主要职责：
    提供一致性的数据擦除手段，确保文档数据的彻底销毁。

    副作用/执行链：
    不仅删除关系型数据库中的记录，还需同步清理 VectorStore 中的向量片段，以及磁盘上的物理文件。
    注意：使用 `missing_ok=True` 防止物理文件丢失导致数据库记录无法删除，
    保证删除接口的幂等性和容错性。

    Args:
        request: FastAPI 请求，用于获取全局配置。
        document_id: 待删除文档的 UUID。
        session: 数据库会话。
        _current_user: 权限依赖。
    """
    document = session.get(Document, document_id)
    if not document:
        raise AppError(404, "document_not_found", "文档不存在")

    # 查询需要清理的所有向量块 ID
    chunk_ids = list(
        session.scalars(select(DocumentChunk.id).where(DocumentChunk.document_id == document_id))
    )

    # 清理外部向量库数据
    request.app.state.worker.vector_store.delete_chunks(document.knowledge_base_id, chunk_ids)

    # 清理本地物理文件
    (request.app.state.settings.upload_dir / document.stored_filename).unlink(missing_ok=True)

    # 清理关系型数据库记录
    session.delete(document)
    session.commit()
