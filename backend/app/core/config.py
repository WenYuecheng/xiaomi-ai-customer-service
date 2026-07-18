from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_name: str = "小米智能客服机器人"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/app.db"
    upload_dir: Path = Path("./data/uploads")
    chroma_dir: Path = Path("./data/chroma")
    model_artifact_dir: Path = Path("./data/models")
    jwt_secret: str | None = None
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = Field(default=60, ge=5, le=1440)
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    llm_provider: Literal["mock", "openai", "ollama"] = "mock"
    llm_model: str = "mock-grounded-chat"
    embedding_provider: Literal["mock", "openai", "ollama", "bge"] = "mock"
    embedding_model: str = "mock-hash-embedding"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    top_k: int = Field(default=4, ge=1, le=20)
    rerank_candidate_k: int = Field(default=8, ge=1, le=20)
    rerank_min_score: float = Field(default=0.65, ge=0, le=1)
    similarity_threshold: float = Field(default=0.25, ge=0, le=1)
    chunk_size: int = Field(default=800, ge=200, le=4000)
    chunk_overlap: int = Field(default=120, ge=0, le=800)
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    sensitive_words: list[str] = Field(default_factory=lambda: ["支付密码", "银行卡密码"])
    initial_admin_username: str = "admin"
    initial_admin_password: str | None = None
    initial_operator_username: str = "operator"
    initial_operator_password: str | None = None
    initial_user_username: str = "customer"
    initial_user_password: str | None = None

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/"):
            raise ValueError("api_prefix must start with '/' and must not end with '/'")
        return value

    def validate_runtime_secrets(self) -> None:
        if self.app_env == "production" and (not self.jwt_secret or len(self.jwt_secret) < 32):
            raise ValueError("JWT_SECRET must contain at least 32 characters in production")
        uses_openai = self.llm_provider == "openai" or self.embedding_provider == "openai"
        if uses_openai and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI-compatible providers")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime_secrets()
    return settings
