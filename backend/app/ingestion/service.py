"""
文件职责：
定义文档处理流水线的核心逻辑服务。包括具体的文档解析、切分与向量库入库操作。

所属功能：
数据摄入服务（Ingestion Service） - 核心业务服务。

重要机制：
后台耗时操作（IO 和模型推理）均通过此处的 `process_job` 执行，
独立于 HTTP 请求生命周期，通过异步任务调度执行。
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
    处理指定的文档摄入后台任务。

    功能归属：
    文档接入与处理 -> 文档解析入库流水线。

    函数职责：
    读取任务指定的文档物理文件，通过底层解析器进行分块，调用 Embedding 模型，
    最后写入向量数据库，并在关系型数据库落表记录所有的文本块元信息。

    执行链：
    `worker._run` → `process_job` → `load_sections` → `split_sections` → `vector_store.add_chunks`

    Args:
        session_factory: 数据库会话工厂，用于获取独立于 HTTP 请求的会话。
        settings: 应用程序的全局配置。
        vector_store: 向量存储服务，用于写入文本块向量。
        job_id: 待处理的任务 UUID。

    Raises:
        ValueError: 当文档内容为空或切分失败时抛出内部错误。
        Exception: 捕获所有运行时的错误，并在记录任务失败状态后将其静默，避免导致守护线程崩溃。

    错误处理：
    内部通过大 `try-except` 包裹，若发生异常（如解析失败或向量数据库不可用），
    会回滚事务并将错误信息记录在 Job 和 Document 实体中。
    """
    # 建立独立于请求的数据库会话，用于长期驻留的异步任务
    with session_factory() as session:
        job = session.get(ProcessingJob, job_id)
        if not job or job.status != JobStatus.queued:
            return

        # 标记任务开始
        job.status = JobStatus.running
        job.stage = "parsing"
        job.attempts += 1
        job.started_at = datetime.now(UTC)
        document = job.document
        document.status = DocumentStatus.processing
        session.commit()

        try:
            # 1. 物理文件加载与文本段提取
            path = settings.upload_dir / document.stored_filename
            sections = load_sections(path)
            if not sections:
                raise ValueError("文档没有可提取的文本")

            # 更新状态为分块阶段
            job.stage = "splitting"
            session.commit()

            # 2. 文本分块与元数据抽取
            chunks_data = split_sections(sections, document.chunk_size, document.chunk_overlap)
            if not chunks_data:
                raise ValueError("文档切分结果为空")

            # 清理历史可能的残留分块（支持重新索引场景）
            old_chunk_ids = list(
                session.scalars(
                    select(DocumentChunk.id).where(DocumentChunk.document_id == document.id)
                )
            )
            vector_store.delete_chunks(document.knowledge_base_id, old_chunk_ids)
            session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))

            # 3. 构造数据库分块记录
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
            # flush 获取 chunks 的自增 ID
            session.flush()

            # 更新状态为特征嵌入阶段
            job.stage = "embedding"
            session.commit()

            # 4. 执行特征向量化与持久化入库
            vector_store.add_chunks(document.knowledge_base_id, chunks)

            # 5. 完成处理并记录成功状态
            document.status = DocumentStatus.ready
            document.error_message = None
            job.status = JobStatus.succeeded
            job.stage = "completed"
            job.finished_at = datetime.now(UTC)
            session.commit()
        except Exception as exc:
            # 异常处理，确保记录详细错误信息并终止当前处理状态
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
    """
    系统启动时恢复因意外停机而中断的文档处理任务。

    Args:
        session_factory: 数据库会话工厂。

    主要流程:
        查找状态为 `running` 的异常任务，并重置其状态为 `queued` 和 `recovered` 阶段，
        使其能被 JobWorker 再次拾取。
    """
    with session_factory() as session:
        session.execute(
            update(ProcessingJob)
            .where(ProcessingJob.status == JobStatus.running)
            .values(status=JobStatus.queued, stage="recovered")
        )
        session.commit()


def next_queued_job(session_factory: sessionmaker[Session]) -> str | None:
    """
    查询并获取队列中最早等待处理的一个任务的 ID。

    Args:
        session_factory: 数据库会话工厂。

    Returns:
        最早的排队任务 ID (str)，如果没有则返回 None。
    """
    with session_factory() as session:
        return session.scalar(
            select(ProcessingJob.id)
            .where(ProcessingJob.status == JobStatus.queued)
            .order_by(ProcessingJob.created_at)
            .limit(1)
        )
