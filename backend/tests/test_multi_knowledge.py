from io import BytesIO
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

import app.chat.service as chat_service
from alembic import command
from app.core.config import get_settings
from app.ingestion.parsers import extract_product_models
from app.rag.providers import QuestionAnalysis
from tests.conftest import auth_headers
from tests.test_documents import wait_for_job

UPLOAD_FIXTURES = Path(__file__).parents[2] / "data" / "upload-fixtures"


def create_library(client: TestClient, headers: dict[str, str], name: str) -> str:
    response = client.post("/api/v1/knowledge-bases", headers=headers, json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def upload_markdown(
    client: TestClient,
    headers: dict[str, str],
    knowledge_base_id: str,
    filename: str,
    content: str,
) -> None:
    response = client.post(
        "/api/v1/documents/upload",
        headers=headers,
        data={"knowledge_base_id": knowledge_base_id},
        files={"file": (filename, BytesIO(content.encode()), "text/markdown")},
    )
    assert response.status_code == 202, response.text
    assert wait_for_job(client, headers, response.json()["job_id"])["status"] == "succeeded"


def test_chat_searches_multiple_libraries_and_reports_source_library(
    client: TestClient, users: dict[str, str]
) -> None:
    operator = auth_headers(client, "operator", users["operator"])
    core_id = create_library(client, operator, "小米生态核心库-多库测试")
    official_id = create_library(client, operator, "小米中国官方完整知识库-多库测试")
    upload_markdown(
        client,
        operator,
        core_id,
        "xiaomi-17t.md",
        "# 小米 17T\n小米 17T 是手机，电池容量为 7000mAh。",
    )
    upload_markdown(
        client,
        operator,
        official_id,
        "robot-power.md",
        "# 扫地机器人无法开机\n电量不足时，请先靠上充电座充电后再使用。",
    )
    customer = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=customer,
        json={
            "knowledge_base_ids": [core_id, official_id],
            "message": "扫地机器人无法开机怎么排查？",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["knowledge_base_ids"] == [core_id, official_id]
    assert body["knowledge_base_id"] == core_id
    assert body["fallback"] is False
    assert any(source["knowledge_base_id"] == official_id for source in body["sources"])
    assert any(
        source["knowledge_base_name"] == "小米中国官方完整知识库-多库测试"
        for source in body["sources"]
    )
    history = client.get(
        f"/api/v1/conversations/{body['conversation_id']}", headers=customer
    ).json()
    assert history["knowledge_base_ids"] == [core_id, official_id]


def test_chat_rejects_conflicting_legacy_and_multi_library_selection(
    client: TestClient, users: dict[str, str]
) -> None:
    operator = auth_headers(client, "operator", users["operator"])
    first_id = create_library(client, operator, "冲突库一")
    second_id = create_library(client, operator, "冲突库二")
    customer = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=customer,
        json={
            "knowledge_base_id": first_id,
            "knowledge_base_ids": [second_id],
            "message": "测试冲突",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "knowledge_base_selection_conflict"


def test_explicit_new_phone_model_overrides_incompatible_robot_history() -> None:
    apply_current_question_override = getattr(chat_service, "apply_current_question_override", None)
    assert apply_current_question_override is not None
    analysis = QuestionAnalysis(
        intent="troubleshooting",
        rewritten_question="小米17T扫地机器人无法开机怎么排查？",
        product_models=["小米17T"],
        need_retrieval=True,
        confidence=0.95,
    )

    guarded = apply_current_question_override("小米17T", analysis)

    assert guarded.intent == "knowledge_query"
    assert guarded.rewritten_question == "小米 17T 产品介绍"
    assert guarded.product_models == ["小米 17t"]


def test_17t_variants_are_normalized_without_truncating_suffix() -> None:
    assert extract_product_models("小米17T") == ["小米 17t"]
    assert extract_product_models("小米 17T Pro") == ["小米 17t pro"]
    assert extract_product_models("Xiaomi 17T") == ["小米 17t"]


def test_duplicate_selection_is_deduplicated_and_inactive_library_is_rejected(
    client: TestClient, users: dict[str, str]
) -> None:
    operator = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = create_library(client, operator, "多库去重测试")
    customer = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=customer,
        json={"knowledge_base_ids": [knowledge_base_id, knowledge_base_id], "message": "无结果"},
    )
    assert response.status_code == 200
    assert response.json()["knowledge_base_ids"] == [knowledge_base_id]

    update = client.patch(
        f"/api/v1/knowledge-bases/{knowledge_base_id}",
        headers=operator,
        json={"status": "archived"},
    )
    assert update.status_code == 200
    rejected = client.post(
        "/api/v1/chat/completions",
        headers=customer,
        json={"knowledge_base_ids": [knowledge_base_id], "message": "不能查询停用库"},
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "knowledge_base_inactive"


def test_chat_and_advisor_accept_five_library_scope(
    client: TestClient, users: dict[str, str]
) -> None:
    operator = auth_headers(client, "operator", users["operator"])
    ids = [create_library(client, operator, f"五库范围-{index}") for index in range(5)]
    customer = auth_headers(client, "customer", users["customer"])

    chat = client.post(
        "/api/v1/chat/completions",
        headers=customer,
        json={"knowledge_base_ids": ids, "message": "知识范围测试"},
    )
    assert chat.status_code == 200, chat.text
    assert chat.json()["knowledge_base_ids"] == ids

    advisor = client.post(
        "/api/v1/advisor/sessions",
        headers=customer,
        json={"knowledge_base_ids": ids, "message": "帮我选购手机"},
    )
    assert advisor.status_code == 200, advisor.text
    assert advisor.json()["session"]["knowledge_base_ids"] == ids


def test_all_retained_upload_fixtures_are_processed_and_chunked(
    client: TestClient, users: dict[str, str]
) -> None:
    operator = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = create_library(client, operator, "文件上传验收库-自动化")
    media_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }
    markers = {
        ".pdf": "UPLOAD-PDF-20260723",
        ".docx": "UPLOAD-DOCX-20260723",
        ".txt": "UPLOAD-TXT-20260723",
        ".md": "UPLOAD-MD-20260723",
    }
    for path in sorted(UPLOAD_FIXTURES.glob("upload-verification.*")):
        response = client.post(
            "/api/v1/documents/upload",
            headers=operator,
            data={"knowledge_base_id": knowledge_base_id},
            files={"file": (path.name, BytesIO(path.read_bytes()), media_types[path.suffix])},
        )
        assert response.status_code == 202, response.text
        assert wait_for_job(client, operator, response.json()["job_id"])["status"] == "succeeded"
        chunks = client.get(
            f"/api/v1/documents/{response.json()['document_id']}/chunks", headers=operator
        ).json()["items"]
        assert any(markers[path.suffix] in chunk["text"] for chunk in chunks)


def test_alembic_backfills_legacy_chat_and_advisor_scopes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "legacy.db"
    database_url = f"sqlite:///{database_path}"
    project_root = Path(__file__).parents[2]
    config = Config(str(project_root / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "backend" / "alembic"))
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    command.upgrade(config, "3c7d9a2e4f10")
    engine = create_engine(database_url)
    now = "2026-07-23 00:00:00"
    with engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO users
            (id, username, display_name, avatar_key, password_hash, role, is_active,
             token_version, created_at)
            VALUES ('u1', 'legacy', 'legacy', 'aurora', 'hash', 'user', 1, 0, :now)"""),
            {"now": now},
        )
        connection.execute(
            text("""INSERT INTO knowledge_bases
            (id, name, description, status, embedding_model, owner_id, created_at, updated_at)
            VALUES ('kb1', '旧知识库', NULL, 'active', 'mock', 'u1', :now, :now)"""),
            {"now": now},
        )
        connection.execute(
            text("""INSERT INTO conversations
            (id, user_id, knowledge_base_id, summary, summary_message_count,
             consecutive_fallbacks, created_at, updated_at)
            VALUES ('c1', 'u1', 'kb1', NULL, 0, 0, :now, :now)"""),
            {"now": now},
        )
        connection.execute(
            text("""INSERT INTO advisor_sessions
            (id, user_id, knowledge_base_id, title, category, created_at, updated_at)
            VALUES ('a1', 'u1', 'kb1', '旧方案', 'phone', :now, :now)"""),
            {"now": now},
        )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert (
            connection.execute(
                text(
                    """SELECT knowledge_base_id FROM conversation_knowledge_bases
                    WHERE conversation_id='c1'"""
                )
            ).scalar_one()
            == "kb1"
        )
        assert (
            connection.execute(
                text(
                    """SELECT knowledge_base_id FROM advisor_session_knowledge_bases
                    WHERE advisor_session_id='a1'"""
                )
            ).scalar_one()
            == "kb1"
        )
    get_settings.cache_clear()
