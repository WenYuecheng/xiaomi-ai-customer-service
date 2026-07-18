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
    name = Path((filename or "").replace("\\", "/")).name.strip()
    if not name or len(name) > 255:
        raise AppError(400, "invalid_filename", "文件名无效")
    return name


def validate_signature(suffix: str, content: bytes) -> None:
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
    settings = request.app.state.settings
    knowledge_base = session.get(KnowledgeBase, knowledge_base_id)
    if not knowledge_base:
        raise AppError(404, "knowledge_base_not_found", "知识库不存在")
    name = safe_original_name(file.filename)
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise AppError(415, "unsupported_file_type", "仅支持 PDF、DOCX、TXT 和 MD")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise AppError(413, "file_too_large", "文件超过大小限制")
    if not content:
        raise AppError(400, "empty_file", "文件内容为空")
    validate_signature(suffix, content)
    actual_chunk_size = chunk_size or settings.chunk_size
    actual_overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap
    if actual_overlap >= actual_chunk_size:
        raise AppError(422, "invalid_chunk_config", "chunk_overlap 必须小于 chunk_size")
    stored_name = f"{uuid4()}{suffix}"
    target = (settings.upload_dir / stored_name).resolve()
    base = settings.upload_dir.resolve()
    if target.parent != base:
        raise AppError(400, "invalid_filename", "文件存储路径无效")
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
        session.rollback()
        target.unlink(missing_ok=True)
        raise AppError(409, "document_exists", "该知识库已存在相同文件") from exc
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
    document = session.get(Document, document_id)
    if not document:
        raise AppError(404, "document_not_found", "文档不存在")
    chunk_ids = list(
        session.scalars(select(DocumentChunk.id).where(DocumentChunk.document_id == document_id))
    )
    request.app.state.worker.vector_store.delete_chunks(document.knowledge_base_id, chunk_ids)
    (request.app.state.settings.upload_dir / document.stored_filename).unlink(missing_ok=True)
    session.delete(document)
    session.commit()
