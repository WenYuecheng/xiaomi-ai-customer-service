"""
文件职责：
该文件负责 FastAPI 应用程序的初始化和核心配置组装。

所属功能：
应用生命周期管理 / 路由注册

主要流程：
1. 从核心配置获取系统设置并进行安全校验。
2. 配置应用生命周期，包括目录初始化、数据库建表及后台工作线程的启停。
3. 注册各种中间件、全局异常处理机制。
4. 挂载各个业务模块的路由（Router）。
"""

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
    """
    创建并配置 FastAPI 应用程序实例。

    Args:
        settings (Settings | None, optional): 应用程序配置实例。
            如果不提供，则使用默认的 `get_settings()` 获取。

    Returns:
        FastAPI: 组装完成的 FastAPI 应用程序实例。

    Raises:
        无直接抛出的异常，但内部依赖可能会在校验时引发异常（如环境变量不满足要求）。
    """
    # 1. 获取配置并进行运行时安全检查
    settings = settings or get_settings()
    settings.validate_runtime_secrets()

    # 初始化数据库引擎和会话工厂
    engine, session_factory = create_database(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        """
        管理 FastAPI 应用程序的生命周期（启动前和停止后）。

        主要职责包括：
        1. 确保需要的数据目录存在。
        2. 确保数据库表结构已创建。
        3. 启动用于处理后台任务的工作线程（Worker）。
        4. 在应用关闭时，优雅地停止工作线程并清理数据库引擎。
        """
        # 确保关键目录存在
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        settings.model_artifact_dir.mkdir(parents=True, exist_ok=True)

        # 初始化数据库表结构
        Base.metadata.create_all(engine)

        # 启动后台任务队列的工作线程
        worker = JobWorker(session_factory, settings)
        application.state.worker = worker
        worker.start()

        yield  # 应用在此期间运行

        # 应用关闭阶段：停止工作线程，销毁引擎
        worker.stop()
        engine.dispose()

    # 2. 实例化 FastAPI 应用
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="基于可信 RAG 的课程演示智能客服平台",
        lifespan=lifespan,
    )

    # 注入全局状态，供路由和依赖项使用
    application.state.settings = settings
    application.state.session_factory = session_factory
    application.state.cancelled_runs = set()
    application.state.registration_rate_limiter = RegistrationRateLimiter(
        settings.registration_rate_limit,
        settings.registration_rate_window_seconds,
    )

    # 3. 注册中间件
    # 请求 ID 中间件，用于全链路追踪
    application.add_middleware(RequestIdMiddleware)
    # CORS 中间件，控制跨域访问
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    # 4. 注册全局异常处理器
    # 处理自定义的业务异常
    application.add_exception_handler(AppError, app_error_handler)
    # 处理请求参数校验异常
    application.add_exception_handler(RequestValidationError, validation_error_handler)

    # 5. 组装路由
    root_router = APIRouter(prefix=settings.api_prefix)

    @root_router.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """
        健康检查接口，用于监控系统状态。

        Returns:
            dict: 包含状态和应用名称的字典。
        """
        return {"status": "ok", "service": settings.app_name}

    # 包含所有业务模块的子路由
    root_router.include_router(auth_router)
    root_router.include_router(account_router)
    root_router.include_router(knowledge_router)
    root_router.include_router(ingestion_router)
    root_router.include_router(chat_router)
    root_router.include_router(advisor_router)
    root_router.include_router(operations_router)

    # 将包含前缀的主路由挂载到应用上
    application.include_router(root_router)
    return application


# 供运行容器（如 uvicorn）使用的 ASGI 应用实例
app = create_app()
