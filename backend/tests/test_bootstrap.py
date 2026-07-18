from importlib.util import find_spec

import pytest

from app.core.config import Settings


def test_application_package_exists() -> None:
    assert find_spec("app") is not None, "FastAPI application package has not been implemented"


def test_openai_compatible_provider_requires_key_at_startup() -> None:
    settings = Settings(
        app_env="test",
        llm_provider="openai",
        openai_api_key=None,
        jwt_secret="test-secret-with-at-least-thirty-two-characters",  # noqa: S106
    )

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        settings.validate_runtime_secrets()
