"""
文件职责：
定义文档处理流水线的核心逻辑服务。包括具体的文档解析、切分与向量库入库操作。

所属功能：
文档接入与处理 -> 核心业务服务。

重要机制：
所有的后台耗时操作（IO和模型推理）均通过此处的 `process_job` 执行，独立于 HTTP 请求生命周期之外。
"""

from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.models import (
    DocumentChunk,
    DocumentStatus,
    JobStatus,
    ProcessingJob,
)
from app.ingestion.parsers import load_sections, split_sections
from app.rag.vector_store import VectorStoreService


def process_job(
    session_factory: sessionmaker[Session],
    settings: Settings,
    vector_store: VectorStoreService,
    job_id: str,
) -> None:
    """
    功能归属：
    文档接入与处理 -> 文档解析入库流水线。

    函数职责：
    读取任务指定的文档物理文件，通过 Langchain 分块，调用 Embedding 模型，
    最后写入向量数据库，并在关系型数据库落表记录。

    执行链：
    `worker._run` → `process_job` → `load_sections` → `split_sections` → `vector_store.add_chunks`

    错误处理：
    内部通过大 `try-except` 包裹，若发生异常（如解析失败或向量数据库不可用），
    会回滚事务并将错误信息记录在 Job 和 Document 实体中。
    """
    # 建立独立于请求的会话
    with session_factory() as session:
        job = session.get(ProcessingJob, job_id)
        if not job or job.status != JobStatus.queued:
            return
        job.status = JobStatus.running
        job.stage = "parsing"
        job.attempts += 1
        job.started_at = datetime.now(UTC)
        document = job.document
        document.status = DocumentStatus.processing
        session.commit()

        try:
            path = settings.upload_dir / document.stored_filename
            sections = load_sections(path)
            if not sections:
                raise ValueError("文档没有可提取的文本")
            job.stage = "splitting"
            session.commit()
            chunks_data = split_sections(sections, document.chunk_size, document.chunk_overlap)
            if not chunks_data:
                raise ValueError("文档切分结果为空")
            old_chunk_ids = list(
                session.scalars(
                    select(DocumentChunk.id).where(DocumentChunk.document_id == document.id)
                )
            )
            vector_store.delete_chunks(document.knowledge_base_id, old_chunk_ids)
            session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
            chunks = [
                DocumentChunk(
                    document_id=document.id,
                    knowledge_base_id=document.knowledge_base_id,
                    ordinal=index,
                    text=text,
                    location=location,
                    product_models=models,
                )
                for index, (text, location, models) in enumerate(chunks_data)
            ]
            session.add_all(chunks)
            session.flush()
            job.stage = "embedding"
            session.commit()
            vector_store.add_chunks(document.knowledge_base_id, chunks)
            document.status = DocumentStatus.ready
            document.error_message = None
            job.status = JobStatus.succeeded
            job.stage = "completed"
            job.finished_at = datetime.now(UTC)
            session.commit()
        except Exception as exc:
            session.rollback()
            job = session.get(ProcessingJob, job_id)
            if job:
                job.status = JobStatus.failed
                job.stage = "failed"
                job.error_message = str(exc)[:1000]
                job.finished_at = datetime.now(UTC)
                job.document.status = DocumentStatus.failed
                job.document.error_message = str(exc)[:1000]
                session.commit()


def recover_interrupted_jobs(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        session.execute(
            update(ProcessingJob)
            .where(ProcessingJob.status == JobStatus.running)
            .values(status=JobStatus.queued, stage="recovered")
        )
        session.commit()


def next_queued_job(session_factory: sessionmaker[Session]) -> str | None:
    with session_factory() as session:
        return session.scalar(
            select(ProcessingJob.id)
            .where(ProcessingJob.status == JobStatus.queued)
            .order_by(ProcessingJob.created_at)
            .limit(1)
        )
