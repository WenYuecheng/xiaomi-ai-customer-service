import json
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.models import BehaviorEvent, MockOrder, User
from tests.conftest import auth_headers
from tests.test_documents import create_knowledge_base, wait_for_job


def seed_order(application: FastAPI, username: str = "customer") -> None:
    with application.state.session_factory() as session:
        user = session.query(User).filter_by(username=username).one()
        session.add(
            MockOrder(
                user_id=user.id,
                order_no="MOCK-20260717-001",
                product_name="小米 14",
                payment_status="已支付",
                shipping_status="运输中",
                logistics=["仓库已出库", "运输中"],
            )
        )
        session.commit()


def prepare_chat_data(client: TestClient, users: dict[str, str]) -> tuple[dict[str, str], str]:
    operator_headers = auth_headers(client, "operator", users["operator"])
    knowledge_base_id = create_knowledge_base(client, operator_headers)
    upload = client.post(
        "/api/v1/documents/upload",
        headers=operator_headers,
        data={"knowledge_base_id": knowledge_base_id},
        files={
            "file": (
                "products.md",
                BytesIO(
                    (
                        "小米 14 支持 90W 快充。\nRedmi K70 适合游戏用户。\n米家 P10 支持自动集尘。"
                    ).encode()
                ),
                "text/markdown",
            )
        },
    ).json()
    wait_for_job(client, operator_headers, upload["job_id"])
    return operator_headers, knowledge_base_id


def test_mock_orders_are_user_isolated_and_clearly_marked(
    client: TestClient, application: FastAPI, users: dict[str, str]
) -> None:
    seed_order(application)
    headers = auth_headers(client, "customer", users["customer"])

    response = client.get("/api/v1/mock/orders", headers=headers)

    assert response.status_code == 200
    assert response.json()[0]["order_no"] == "MOCK-20260717-001"
    assert response.json()[0]["is_mock"] is True


def test_order_intent_routes_to_mock_tool(
    client: TestClient, application: FastAPI, users: dict[str, str]
) -> None:
    seed_order(application)
    operator_headers, knowledge_base_id = prepare_chat_data(client, users)
    del operator_headers
    headers = auth_headers(client, "customer", users["customer"])

    response = client.post(
        "/api/v1/chat/completions",
        headers=headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "我的订单物流到哪里了？"},
    )

    assert response.status_code == 200
    assert response.json()["fallback"] is False
    assert response.json()["sources"] == []
    assert "Mock 演示数据" in response.json()["answer"]
    assert "运输中" in response.json()["answer"]


def test_ticket_can_be_created_from_conversation(client: TestClient, users: dict[str, str]) -> None:
    _, knowledge_base_id = prepare_chat_data(client, users)
    headers = auth_headers(client, "customer", users["customer"])
    chat = client.post(
        "/api/v1/chat/completions",
        headers=headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "小米 14 无法开机，请转人工"},
    ).json()

    response = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={"conversation_id": chat["conversation_id"], "priority": "high"},
    )

    assert response.status_code == 201
    assert response.json()["conversation_id"] == chat["conversation_id"]
    assert "小米 14" in response.json()["summary"]
    assert response.json()["status"] == "open"

    duplicate = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={"conversation_id": chat["conversation_id"], "priority": "urgent"},
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == response.json()["id"]

    operator_headers = auth_headers(client, "operator", users["operator"])
    update = client.patch(
        f"/api/v1/tickets/{response.json()['id']}",
        headers=operator_headers,
        json={"status": "resolved", "priority": "urgent"},
    )
    assert update.status_code == 200
    assert update.json()["status"] == "resolved"
    assert update.json()["priority"] == "urgent"


def test_hot_topics_profile_recommendations_and_training(
    client: TestClient,
    application: FastAPI,
    users: dict[str, str],
    settings,
) -> None:
    operator_headers, knowledge_base_id = prepare_chat_data(client, users)
    user_headers = auth_headers(client, "customer", users["customer"])
    for question in ("小米 14 充电怎么样？", "小米 14 适合游戏吗？", "Redmi K70 怎么样？"):
        client.post(
            "/api/v1/chat/completions",
            headers=user_headers,
            json={"knowledge_base_id": knowledge_base_id, "message": question},
        )

    topics = client.get("/api/v1/operations/hot-topics?window=day", headers=operator_headers)
    profile = client.get("/api/v1/operations/profile/me", headers=user_headers)
    recommendations = client.get(
        f"/api/v1/recommendations?knowledge_base_id={knowledge_base_id}", headers=user_headers
    )
    with application.state.session_factory() as session:
        for username, questions in {
            "admin": ["小米 14", "Redmi K70", "米家 P10"],
            "operator": ["Redmi K70", "米家 P10", "小米 14"],
        }.items():
            user = session.query(User).filter_by(username=username).one()
            session.add_all(
                BehaviorEvent(
                    user_id=user.id,
                    event_type="chat",
                    payload={"question": question, "intent": "knowledge_query"},
                )
                for question in questions
            )
        session.commit()
    training = client.post("/api/v1/recommendation/training-runs", headers=operator_headers)

    assert topics.status_code == 200
    assert any("小米" in item["term"] for item in topics.json()["items"])
    assert topics.json()["heatmap"]
    assert profile.status_code == 200
    assert "小米 14" in profile.json()["product_preferences"]
    assert recommendations.status_code == 200
    assert recommendations.json()["items"]
    assert training.status_code == 201
    assert training.json()["status"] == "succeeded"
    assert 0 <= training.json()["precision_at_k"] <= 1
    assert Path(settings.model_artifact_dir, training.json()["artifact_filename"]).exists()
    artifact = json.loads(
        Path(settings.model_artifact_dir, training.json()["artifact_filename"]).read_text()
    )
    assert artifact["dataset"] == "observed-user-behavior"
    runs = client.get("/api/v1/recommendation/training-runs", headers=operator_headers)
    assert runs.status_code == 200
    assert runs.json()[0]["id"] == training.json()["id"]


def test_knowledge_analytics_graph_and_training_explanation(
    client: TestClient,
    application: FastAPI,
    users: dict[str, str],
) -> None:
    operator_headers, knowledge_base_id = prepare_chat_data(client, users)

    analytics = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/analytics",
        headers=operator_headers,
    )
    graph = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/graph",
        headers=operator_headers,
    )

    assert analytics.status_code == 200
    assert analytics.json()["document_count"] == 1
    assert analytics.json()["chunk_count"] >= 1
    assert analytics.json()["product_count"] >= 3
    assert analytics.json()["source_coverage"] == 0
    assert graph.status_code == 200
    assert any(node["kind"] == "knowledge_base" for node in graph.json()["nodes"])
    assert any(node["kind"] == "product" for node in graph.json()["nodes"])
    assert graph.json()["edges"]

    with application.state.session_factory() as session:
        for username, questions in {
            "admin": ["小米 14", "Redmi K70", "米家 P10"],
            "operator": ["Redmi K70", "米家 P10", "小米 14"],
        }.items():
            user = session.query(User).filter_by(username=username).one()
            session.add_all(
                BehaviorEvent(
                    user_id=user.id,
                    event_type="chat",
                    payload={"question": question, "intent": "knowledge_query"},
                )
                for question in questions
            )
        session.commit()

    first = client.post(
        "/api/v1/recommendation/training-runs",
        headers=operator_headers,
        json={"target": "balanced"},
    )
    duplicate = client.post(
        "/api/v1/recommendation/training-runs",
        headers=operator_headers,
        json={"target": "balanced"},
    )

    assert first.status_code == 201
    assert first.json()["changed"] is True
    assert first.json()["target"] == "balanced"
    assert first.json()["sample_count"] == 2
    assert first.json()["product_count"] == 3
    assert first.json()["k"] == 3
    assert "留出" in first.json()["explanation"]
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == first.json()["id"]
    assert duplicate.json()["changed"] is False

    precision_run = client.post(
        "/api/v1/recommendation/training-runs",
        headers=operator_headers,
        json={"target": "precision"},
    )
    assert precision_run.status_code == 201
    assert precision_run.json()["id"] != first.json()["id"]
    assert precision_run.json()["k"] == 1
    assert precision_run.json()["metric_delta"]["precision"] is not None
