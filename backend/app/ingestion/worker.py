"""
文件职责：
该文件负责后台异步任务消费器的线程实现。

所属功能：
数据摄入服务（Ingestion Service） - 异步任务队列处理

主要流程：
系统启动时实例化单例 `JobWorker` 并启动守护线程。该线程从数据库表中获取排队任务，循环消费执行处理。
使用 `threading.Event` 机制避免无任务时的无效空转和频繁数据库轮询，
提升系统性能和资源利用率。
"""

from threading import Event, Thread

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.ingestion.service import next_queued_job, process_job, recover_interrupted_jobs
from app.rag.vector_store import VectorStoreService, create_embeddings


class JobWorker:
    """
    负责管理后台处理任务调度的核心工作器类。

    主要职责：
    作为后台调度实体，负责将待处理的文档处理任务（如分块、向量化）从数据库队列取出并调用服务层进行处理。

    生命周期：
    在应用启动时初始化并调用 start()，随后持续在后台以守护线程运行。
    应用关闭时调用 stop() 优雅退出。
    """

    def __init__(self, session_factory: sessionmaker[Session], settings: Settings) -> None:
        """
        初始化 JobWorker 实例。

        Args:
            session_factory: 用于创建数据库会话的工厂函数。
            settings: 应用程序的全局配置信息。
        """
        self.session_factory = session_factory
        self.settings = settings
        self.vector_store = VectorStoreService(settings.chroma_dir, create_embeddings(settings))
        # 用于控制工作线程的停止
        self._stop = Event()
        # 用于唤醒休眠的工作线程
        self._wake = Event()
        # 初始化守护线程
        self._thread = Thread(target=self._run, name="document-worker", daemon=True)

    def start(self) -> None:
        """
        启动后台工作线程。

        在启动前，会先调用 recover_interrupted_jobs 恢复并重新排队可能因上次意外停机而中断的任务。
        """
        recover_interrupted_jobs(self.session_factory)
        self._thread.start()

    def notify(self) -> None:
        """
        通知后台线程有新任务到来。

        通过设置唤醒事件 (_wake)，终止线程的 wait 挂起状态，使其立刻进行下一次任务拉取。
        """
        self._wake.set()

    def stop(self) -> None:
        """
        停止后台工作线程。

        发出停止信号并唤醒线程，最后等待最多 5 秒钟以便当前任务优雅完成。
        """
        self._stop.set()
        self._wake.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        """
        内部的无限工作循环逻辑。

        HOW IT WORKS:
        尝试拉取待处理任务，如果有就立刻执行 `process_job`。
        如果没有，则调用 `_wake.wait` 挂起等待最多 0.25 秒或直到外部调用 `notify` 唤醒。
        这样既避免了持续轮询过度占用 CPU，又保证了新任务能得到及时响应。
        """
        while not self._stop.is_set():
            job_id = next_queued_job(self.session_factory)
            if job_id:
                process_job(self.session_factory, self.settings, self.vector_store, job_id)
                continue
            self._wake.wait(timeout=0.25)
            self._wake.clear()
