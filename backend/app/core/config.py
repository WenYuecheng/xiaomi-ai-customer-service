"""
文件职责：
该文件负责全系统配置的加载与管理，通过环境变量和 `.env` 文件初始化应用配置。

所属功能：
核心基础设施 -> 配置管理。

主要流程：
1. 声明所有配置项的类型、默认值和取值范围。
2. 启动时从环境变量或 `.env` 文件加载实际值。
3. 对关键配置（如路径格式、安全密钥）进行运行时校验。

主要调用方：
全局单例依赖，几乎所有需要配置的模块都会调用 `get_settings` 获取实例。

主要依赖：
pydantic_settings。

副作用：
无副作用，纯内存配置对象。
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    主要职责：
    系统全局配置对象，提供类型安全的配置读取。

    所属功能：
    核心基础设施 -> 配置管理。

    生命周期：
    应用启动时实例化并被 `get_settings` 缓存，生命周期与应用一致。
    """

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
    registration_rate_limit: int = Field(default=5, ge=1, le=100)
    registration_rate_window_seconds: int = Field(default=600, ge=60, le=86400)
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
        """
        验证 API 路由前缀格式。必须以斜杠开头，不能以斜杠结尾，如 `/api/v1`。
        """
        if not value.startswith("/") or value.endswith("/"):
            raise ValueError("api_prefix must start with '/' and must not end with '/'")
        return value

    def validate_runtime_secrets(self) -> None:
        """
        功能归属：
        核心基础设施 -> 配置管理 -> 安全检查。

        函数职责：
        检查当前环境是否缺少必要的敏感密钥配置。

        流程位置：
        在配置实例化完成后（`get_settings`内部）以及应用启动（`main.py`）时调用。

        异常：
        - 生产环境下如果 JWT_SECRET 长度不足抛出 ValueError。
        - 如果启用了 OpenAI 系列模型但未配置 API_KEY 抛出 ValueError。
        """
        # 生产环境强制要求强随机密钥，防止伪造 JWT
        if self.app_env == "production" and (not self.jwt_secret or len(self.jwt_secret) < 32):
            raise ValueError("JWT_SECRET must contain at least 32 characters in production")

        # 检查是否使用了需要外部 API 的模型提供商
        uses_openai = self.llm_provider == "openai" or self.embedding_provider == "openai"
        if uses_openai and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI-compatible providers")


@lru_cache
def get_settings() -> Settings:
    """
    功能归属：
    核心基础设施 -> 配置管理。

    函数职责：
    返回全局唯一的配置实例。通过 `lru_cache` 保证只解析一次环境变量。

    调用方：
    被系统内各类组件、路由器或依赖注入调用。
    """
    settings = Settings()
    settings.validate_runtime_secrets()
    return settings
