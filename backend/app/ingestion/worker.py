"""
文件职责：
后台异步任务消费器的线程实现。

所属功能：
文档接入与处理 -> 异步任务队列。

主要流程：
系统启动时实例化单例 `JobWorker` 并启动守护线程。该线程从数据库表中获取排队任务，循环消费执行处理。
使用 `Event` 机制避免无任务时的无效空转（数据库轮询）。
"""

from threading import Event, Thread

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.ingestion.service import next_queued_job, process_job, recover_interrupted_jobs
from app.rag.vector_store import VectorStoreService, create_embeddings


class JobWorker:
    """
    主要职责：
    后台调度实体，负责将待处理的文档转换为处理任务传递给服务层。
    包含内部的生命周期管理 (start, notify, stop)。
    """

    def __init__(self, session_factory: sessionmaker[Session], settings: Settings) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.vector_store = VectorStoreService(settings.chroma_dir, create_embeddings(settings))
        self._stop = Event()
        self._wake = Event()
        self._thread = Thread(target=self._run, name="document-worker", daemon=True)

    def start(self) -> None:
        recover_interrupted_jobs(self.session_factory)
        self._thread.start()

    def notify(self) -> None:
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        """
        内部工作循环：
        尝试拉取待处理任务，如果有就立刻执行。
        如果没有，则挂起等待最多 0.25 秒或直到外部调用 `notify` 唤醒，避免过度占用 CPU。
        """
        while not self._stop.is_set():
            job_id = next_queued_job(self.session_factory)
            if job_id:
                process_job(self.session_factory, self.settings, self.vector_store, job_id)
                continue
            self._wake.wait(timeout=0.25)
            self._wake.clear()
