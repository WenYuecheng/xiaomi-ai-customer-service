from fastapi import APIRouter, FastAPI

from app.core.config import get_settings
from app.core.http import RequestIdMiddleware

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="基于可信 RAG 的课程演示智能客服平台",
)
app.add_middleware(RequestIdMiddleware)

router = APIRouter(prefix=settings.api_prefix)


@router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


app.include_router(router)

