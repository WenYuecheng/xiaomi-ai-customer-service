from threading import Event, Thread

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.ingestion.service import next_queued_job, process_job, recover_interrupted_jobs
from app.rag.vector_store import VectorStoreService


class JobWorker:
    def __init__(self, session_factory: sessionmaker[Session], settings: Settings) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.vector_store = VectorStoreService(settings.chroma_dir)
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
        while not self._stop.is_set():
            job_id = next_queued_job(self.session_factory)
            if job_id:
                process_job(self.session_factory, self.settings, self.vector_store, job_id)
                continue
            self._wake.wait(timeout=0.25)
            self._wake.clear()

