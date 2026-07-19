"""
文件职责：
该文件负责验证核心业务操作流与相关功能的集成测试。

所属功能：
订单管理、客服会话流转、工单系统与业务数据分析模块。

主要流程：
包含订单的模拟注入、聊天数据的准备，以及订单隔离、意图路由、工单自动创建、热点话题与用户画像统计和知识库图谱分析等综合业务场景的测试。
"""

import json
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.models import BehaviorEvent, MockOrder, User
from tests.conftest import auth_headers
from tests.test_documents import create_knowledge_base, wait_for_job


def seed_order(application: FastAPI, username: str = "customer") -> None:
    """
    在数据库中为特定用户注入一条模拟订单记录，用于后续测试。

    Args:
        application: FastAPI 应用实例，用于获取数据库会话工厂。
        username: 需要注入模拟订单的用户名，默认 "customer"。

    Returns:
        None
    """
    # 开启数据库会话
    with application.state.session_factory() as session:
        # 查询目标用户
        user = session.query(User).filter_by(username=username).one()
        # 构造并添加 Mock 订单
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
        # 提交事务以持久化该订单
        session.commit()


def prepare_chat_data(client: TestClient, users: dict[str, str]) -> tuple[dict[str, str], str]:
    """
    测试辅助函数：准备一个基础的客服知识库及关联文档。

    通过模拟运营人员身份，创建知识库并上传一段包含产品信息的测试文档，以供问答测试使用。

    Args:
        client: FastAPI 测试客户端。
        users: 测试用户字典。

    Returns:
        tuple[dict[str, str], str]: 返回运营人员鉴权头和刚创建的知识库 ID。
    """
    # 获取运营人员（operator）身份鉴权头
    operator_headers = auth_headers(client, "operator", users["operator"])
    # 建立测试用知识库
    knowledge_base_id = create_knowledge_base(client, operator_headers)

    # 上传预设的产品详情 Markdown 文档
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

    # 必须等待异步文档解析切块任务完成，否则后续查询无法命中数据
    wait_for_job(client, operator_headers, upload["job_id"])

    return operator_headers, knowledge_base_id


def test_mock_orders_are_user_isolated_and_clearly_marked(
    client: TestClient, application: FastAPI, users: dict[str, str]
) -> None:
    """
    测试 Mock 订单的数据隔离及属性标记。

    验证某个用户能否正常获取自己的订单，并确保这些订单被明确打上了 mock 标记，以避免和真实订单混淆。

    Args:
        client: 测试客户端。
        application: FastAPI 应用。
        users: 测试用户字典。
    """
    # 注入该客户的模拟订单数据
    seed_order(application)
    # 获取客户（customer）身份鉴权头
    headers = auth_headers(client, "customer", users["customer"])

    # 客户查询自己的模拟订单列表
    response = client.get("/api/v1/mock/orders", headers=headers)

    # 校验：接口成功响应
    assert response.status_code == 200
    # 校验：返回的订单号匹配注入的数据
    assert response.json()[0]["order_no"] == "MOCK-20260717-001"
    # 校验：返回数据确实带有安全沙盒中要求的 is_mock=True 标记
    assert response.json()[0]["is_mock"] is True


def test_order_intent_routes_to_mock_tool(
    client: TestClient, application: FastAPI, users: dict[str, str]
) -> None:
    """
    测试聊天意图能否正确路由到 Mock 订单工具。

    验证当用户询问订单物流时，系统意图识别机制能够自动调用查询订单函数，并将结果整合回复给用户。

    Args:
        client: 测试客户端。
        application: FastAPI 应用。
        users: 测试用户字典。
    """
    # 准备订单数据
    seed_order(application)
    # 准备知识库以防大模型回退
    operator_headers, knowledge_base_id = prepare_chat_data(client, users)
    del operator_headers
    # 获取客户（customer）请求头
    headers = auth_headers(client, "customer", users["customer"])

    # 发送询问订单物流的聊天请求
    response = client.post(
        "/api/v1/chat/completions",
        headers=headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "我的订单物流到哪里了？"},
    )

    # 校验：对话接口响应成功
    assert response.status_code == 200
    # 校验：大模型没有因无法处理而触发 fallback
    assert response.json()["fallback"] is False
    # 校验：没有使用检索知识库的数据（因为是调用了订单工具，而非知识库查询）
    assert response.json()["sources"] == []
    # 校验：回复中包含由于工具模拟数据而特有的提示语句
    assert "Mock 演示数据" in response.json()["answer"]
    # 校验：回复中提取到了订单实际状态（如"运输中"）
    assert "运输中" in response.json()["answer"]


def test_ticket_can_be_created_from_conversation(client: TestClient, users: dict[str, str]) -> None:
    """
    测试从现有对话上下文中创建人工工单 (Ticket) 的完整流转。

    包含：从对话总结创建新工单、防止针对同一对话重复创建，以及运营人员后续更新工单状态的权限流验证。

    Args:
        client: 测试客户端。
        users: 测试用户字典。
    """
    _, knowledge_base_id = prepare_chat_data(client, users)
    headers = auth_headers(client, "customer", users["customer"])

    # 模拟客户发起一条包含明显求助意向的对话，获取 conversation_id
    chat = client.post(
        "/api/v1/chat/completions",
        headers=headers,
        json={"knowledge_base_id": knowledge_base_id, "message": "小米 14 无法开机，请转人工"},
    ).json()

    # 根据上述对话 ID 创建一个新的工单
    response = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={"conversation_id": chat["conversation_id"], "priority": "high"},
    )

    # 校验：工单应成功创建 (201 Created)
    assert response.status_code == 201
    assert response.json()["conversation_id"] == chat["conversation_id"]
    # 校验：服务端应基于对话历史自动提取到了包含“小米 14”的摘要信息
    assert "小米 14" in response.json()["summary"]
    # 校验：初始状态为 open
    assert response.json()["status"] == "open"

    # 测试防重复控制：向同一对话再次尝试创建工单
    duplicate = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={"conversation_id": chat["conversation_id"], "priority": "urgent"},
    )
    # 校验：应直接返回已有工单，并带有 201 或者相同资源（视业务幂等性决定，此处仍为201及相同ID）
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == response.json()["id"]

    # 模拟客服（operator）接管，流转更新工单状态及优先级
    operator_headers = auth_headers(client, "operator", users["operator"])
    update = client.patch(
        f"/api/v1/tickets/{response.json()['id']}",
        headers=operator_headers,
        json={"status": "resolved", "priority": "urgent"},
    )

    # 校验：修改成功，且各字段均已被覆盖更新
    assert update.status_code == 200
    assert update.json()["status"] == "resolved"
    assert update.json()["priority"] == "urgent"


def test_hot_topics_profile_recommendations_and_training(
    client: TestClient,
    application: FastAPI,
    users: dict[str, str],
    settings,
) -> None:
    """
    测试热点话题聚合、用户画像生成、以及基于行为的推荐模型训练完整流程。

    本用例模拟产生不同角色的提问事件，由此验证服务端统计聚合分析的准确度，以及调用推荐模型进行训练的过程。

    Args:
        client: 测试客户端。
        application: FastAPI 应用。
        users: 测试用户字典。
        settings: 配置项注入，用于访问产生工件（Artifacts）的目录路径。
    """
    operator_headers, knowledge_base_id = prepare_chat_data(client, users)
    user_headers = auth_headers(client, "customer", users["customer"])

    # 模拟客户连续提问多个产品，由此积累会话分析数据
    for question in ("小米 14 充电怎么样？", "小米 14 适合游戏吗？", "Redmi K70 怎么样？"):
        client.post(
            "/api/v1/chat/completions",
            headers=user_headers,
            json={"knowledge_base_id": knowledge_base_id, "message": question},
        )

    # 运营人员获取过去一天内的热点话题趋势分析
    topics = client.get("/api/v1/operations/hot-topics?window=day", headers=operator_headers)
    # 客户查询根据自己的提问记录自动推演出的用户画像（如偏好产品）
    profile = client.get("/api/v1/operations/profile/me", headers=user_headers)
    # 客户尝试拉取针对自己的产品问答推荐列表
    recommendations = client.get(
        f"/api/v1/recommendations?knowledge_base_id={knowledge_base_id}", headers=user_headers
    )

    # 向数据库直接注入 admin 和 operator 其他人员的模拟历史行为事件，扩充推荐算法的模型训练集
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

    # 运营人员手动触发推荐模型（或相关权重）训练跑批任务
    training = client.post("/api/v1/recommendation/training-runs", headers=operator_headers)

    # 校验各项业务查询返回正确
    assert topics.status_code == 200
    assert any("小米" in item["term"] for item in topics.json()["items"])
    assert topics.json()["heatmap"]
    assert profile.status_code == 200
    assert "小米 14" in profile.json()["product_preferences"]
    assert recommendations.status_code == 200
    assert recommendations.json()["items"]

    # 校验：训练任务成功被触发并执行完毕
    assert training.status_code == 201
    assert training.json()["status"] == "succeeded"
    assert 0 <= training.json()["precision_at_k"] <= 1
    # 校验：训练输出的模型权重/策略文件成功写入本地磁盘工件目录
    assert Path(settings.model_artifact_dir, training.json()["artifact_filename"]).exists()

    # 读取物理工件检查其内部记录的训练来源标记
    artifact = json.loads(
        Path(settings.model_artifact_dir, training.json()["artifact_filename"]).read_text()
    )
    assert artifact["dataset"] == "observed-user-behavior"

    # 检查训练记录列表能否查询到刚跑出的这条记录
    runs = client.get("/api/v1/recommendation/training-runs", headers=operator_headers)
    assert runs.status_code == 200
    assert runs.json()[0]["id"] == training.json()["id"]


def test_knowledge_analytics_graph_and_training_explanation(
    client: TestClient,
    application: FastAPI,
    users: dict[str, str],
) -> None:
    """
    测试知识库的综合数据统计大盘、知识图谱结构图输出以及带目标参数的模型训练和增量训练识别。

    Args:
        client: 测试客户端。
        application: FastAPI 应用。
        users: 测试用户字典。
    """
    operator_headers, knowledge_base_id = prepare_chat_data(client, users)

    # 获知当前知识库统计分析汇总数据
    analytics = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/analytics",
        headers=operator_headers,
    )
    # 抽取结构化图谱节点与边关系图
    graph = client.get(
        f"/api/v1/knowledge-bases/{knowledge_base_id}/graph",
        headers=operator_headers,
    )

    # 校验：分析面板返回数据符合先前注入的一篇文档和三个产品的预期
    assert analytics.status_code == 200
    assert analytics.json()["document_count"] == 1
    assert analytics.json()["chunk_count"] >= 1
    assert analytics.json()["product_count"] >= 3
    assert analytics.json()["source_coverage"] == 0
    # 校验：图谱数据至少包含知识库节点和产品节点种类，且存在关联边
    assert graph.status_code == 200
    assert any(node["kind"] == "knowledge_base" for node in graph.json()["nodes"])
    assert any(node["kind"] == "product" for node in graph.json()["nodes"])
    assert graph.json()["edges"]

    # 向事件表注入用于推荐训练的测试数据集
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

    # 以“平衡”(balanced)作为优化指标，启动首次训练跑批
    first = client.post(
        "/api/v1/recommendation/training-runs",
        headers=operator_headers,
        json={"target": "balanced"},
    )
    # 在数据集未改变时，再次请求相同目标参数的训练
    duplicate = client.post(
        "/api/v1/recommendation/training-runs",
        headers=operator_headers,
        json={"target": "balanced"},
    )

    # 首次训练产生新模型，并反馈样本、产品、推荐广度 K 值和训练原理。
    assert first.status_code == 201
    assert first.json()["changed"] is True
    assert first.json()["target"] == "balanced"
    assert first.json()["sample_count"] == 2
    assert first.json()["product_count"] == 3
    assert first.json()["k"] == 3
    assert "留出" in first.json()["explanation"]
    # 数据未更新且 target 相同时复用上一个模型，不重复训练。
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == first.json()["id"]
    assert duplicate.json()["changed"] is False

    # 改变训练目标参数（如强调 precision 准确率），应抛弃复用，强制重新训练
    precision_run = client.post(
        "/api/v1/recommendation/training-runs",
        headers=operator_headers,
        json={"target": "precision"},
    )
    assert precision_run.status_code == 201
    assert precision_run.json()["id"] != first.json()["id"]
    # precision 训练可能调低了召回广度（k下降）以换取准确
    assert precision_run.json()["k"] == 1
    assert precision_run.json()["metric_delta"]["precision"] is not None
