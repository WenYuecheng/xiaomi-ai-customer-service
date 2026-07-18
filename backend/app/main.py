from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.account.router import router as account_router
from app.advisor.router import router as advisor_router
from app.auth.rate_limit import RegistrationRateLimiter
from app.auth.router import router as auth_router
from app.chat.router import router as chat_router
from app.core.config import Settings, get_settings
from app.core.errors import AppError, app_error_handler, validation_error_handler
from app.core.http import RequestIdMiddleware
from app.db.base import Base, create_database
from app.ingestion.router import router as ingestion_router
from app.ingestion.worker import JobWorker
from app.knowledge.router import router as knowledge_router
from app.operations.router import router as operations_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.validate_runtime_secrets()
    engine, session_factory = create_database(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        settings.model_artifact_dir.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(engine)
        worker = JobWorker(session_factory, settings)
        application.state.worker = worker
        worker.start()
        yield
        worker.stop()
        engine.dispose()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="基于可信 RAG 的课程演示智能客服平台",
        lifespan=lifespan,
    )
    application.state.settings = settings
    application.state.session_factory = session_factory
    application.state.cancelled_runs = set()
    application.state.registration_rate_limiter = RegistrationRateLimiter(
        settings.registration_rate_limit,
        settings.registration_rate_window_seconds,
    )
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    application.add_exception_handler(AppError, app_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)

    root_router = APIRouter(prefix=settings.api_prefix)

    @root_router.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    root_router.include_router(auth_router)
    root_router.include_router(account_router)
    root_router.include_router(knowledge_router)
    root_router.include_router(ingestion_router)
    root_router.include_router(chat_router)
    root_router.include_router(advisor_router)
    root_router.include_router(operations_router)
    application.include_router(root_router)
    return application


app = create_app()
