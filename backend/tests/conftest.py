from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        upload_dir=tmp_path / "uploads",
        chroma_dir=tmp_path / "chroma",
        model_artifact_dir=tmp_path / "models",
        jwt_secret="test-secret-with-at-least-thirty-two-characters",  # noqa: S106
        llm_provider="mock",
        llm_model="mock-grounded-chat",
        embedding_provider="mock",
        embedding_model="mock-hash-embedding",
    )


@pytest.fixture
def application(settings: Settings) -> FastAPI:
    from app.main import create_app

    return create_app(settings)


@pytest.fixture
def client(application: FastAPI) -> Iterator[TestClient]:
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def users(application: FastAPI) -> dict[str, str]:
    from app.auth.service import create_user

    session_factory = application.state.session_factory
    with session_factory() as session:
        create_user(session, "admin", "AdminPass123!", "admin")
        create_user(session, "operator", "OperatorPass123!", "operator")
        create_user(session, "customer", "CustomerPass123!", "user")
    return {
        "admin": "AdminPass123!",
        "operator": "OperatorPass123!",
        "customer": "CustomerPass123!",
    }


def auth_headers(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
