"""
文件职责：
商品推荐与机器学习模型训练模块。
包含一套简易的实时多路召回（倾向性 + 热门）以及一套可训练的 SVD 矩阵分解（协同过滤）离线推荐演示。

所属功能：
运营分析与推荐 -> 推荐引擎核心。

主要流程：
1. `recommend`: 提供给前台接口，融合局部偏好和全局热度。
2. `train_recommender`: 离线定时或手动触发执行矩阵分解模型的训练、评估、版本化及产物打包。
"""

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BehaviorEvent, DocumentChunk, RecommendationTrainingRun
from app.ingestion.parsers import extract_product_models
from app.operations.schemas import RecommendationItem, RecommendationList


@dataclass
class TrainingOutcome:
    run: RecommendationTrainingRun
    metadata: dict
    changed: bool


def recommend(session: Session, user_id: str, knowledge_base_id: str) -> RecommendationList:
    """
    实时推荐算法（基于规则的多路召回加权）。

    主要职责：
    利用公式：推荐得分 = 60% 用户自身历史偏好打分 + 25% 平台全局热门商品打分 + 15% 内容固有权重。

    执行链：
    1. 提取当前用户问过的商品（偏好特征）。
    2. 提取全局用户问过的商品（热度特征）。
    3. 为知识库中存在的所有产品进行上述加权打分，并排序输出前 10 个。
    4. 若用户完全无历史，属于冷启动 (`cold_start`)，则完全依赖全局热度。

    Args:
        session: 数据库会话。
        user_id: 正在获取推荐的用户 UUID。
        knowledge_base_id: 当前约束范围的知识库 ID。

    Returns:
        包含前 10 推荐商品及是否触发冷启动标志的结果。
    """
    chunks = list(
        session.scalars(
            select(DocumentChunk).where(DocumentChunk.knowledge_base_id == knowledge_base_id)
        )
    )
    catalog = sorted({model for chunk in chunks for model in chunk.product_models})
    events = list(
        session.scalars(
            select(BehaviorEvent).where(
                BehaviorEvent.event_type == "chat",
                BehaviorEvent.user_id == user_id,
            )
        )
    )
    preferences: Counter[str] = Counter()
    for event in events:
        preferences.update(extract_product_models(str(event.payload.get("question", ""))))
    global_counts: Counter[str] = Counter()
    for event in session.scalars(select(BehaviorEvent).where(BehaviorEvent.event_type == "chat")):
        global_counts.update(extract_product_models(str(event.payload.get("question", ""))))
    items = []
    maximum = max([*preferences.values(), 1])
    global_maximum = max([*global_counts.values(), 1])
    for index, product in enumerate(catalog):
        preference_score = preferences[product] / maximum
        popularity_score = global_counts[product] / global_maximum
        content_score = 1 / (index + 1)
        score = 0.6 * preference_score + 0.25 * popularity_score + 0.15 * content_score
        reason = "基于你的咨询偏好" if preferences[product] else "知识库热门产品"
        items.append(
            RecommendationItem(product_model=product, score=round(score, 4), reason=reason)
        )
    items.sort(key=lambda item: item.score, reverse=True)
    return RecommendationList(items=items[:10], cold_start=not bool(preferences))


def train_recommender(session: Session, artifact_dir, target: str = "balanced") -> TrainingOutcome:
    """
    离线训练机制：基于用户-物品交互矩阵的 SVD (奇异值分解) 协同过滤模型训练。

    执行链：
    1. 搜集数据库中用户对话里提到的产品作为交互行为。
    2. 当有效用户和有效产品较少时，降级使用内置的静态
       `clearly-labelled-demo-interactions` 演示矩阵。
    3. 通过哈希指纹 `data_fingerprint` 避免数据无变化时的重复训练浪费资源。
    4. 采用留一法（Leave-One-Out）进行模型评估。提取每个用户的最后一个
       点击物品作为预测基准，其余作为训练数据。
    5. 利用 Scikit-Learn 的 `TruncatedSVD` 进行降维和特征提取。
    6. 计算并输出 `Precision@K` 和 `Recall@K`。
    7. 将训练出的矩阵权重作为产物 (Artifact) 持久化成 JSON 文件保存，同时入库历史。

    Args:
        session: 数据库会话。
        artifact_dir: 训练结果文件的持久化存储目录。
        target: 训练评估倾向 ("balanced" | "precision" | "recall")。

    Returns:
        TrainingOutcome 结构，包含当次运行记录、产生的元数据和是否发生真正更新的标志。
    """
    user_preferences: dict[str, Counter[str]] = {}
    for event in session.scalars(select(BehaviorEvent).where(BehaviorEvent.event_type == "chat")):
        models = extract_product_models(str(event.payload.get("question", "")))
        if models:
            user_preferences.setdefault(event.user_id, Counter()).update(models)
    eligible = {user_id: counts for user_id, counts in user_preferences.items() if len(counts) >= 2}
    observed_products = sorted({product for counts in eligible.values() for product in counts})
    if len(eligible) >= 2 and len(observed_products) >= 3:
        products = observed_products
        matrix = np.array(
            [[counts[product] for product in products] for counts in eligible.values()],
            dtype=float,
        )
        dataset_name = "observed-user-behavior"
    else:
        products = ["小米 14", "Redmi K70", "米家 P10", "小米 14 Ultra", "Redmi K70 Pro"]
        matrix = np.array(
            [
                [5, 1, 0, 4, 0],
                [0, 5, 1, 0, 4],
                [1, 0, 5, 0, 0],
                [4, 2, 0, 5, 1],
                [0, 4, 1, 0, 5],
                [2, 1, 4, 0, 0],
            ],
            dtype=float,
        )
        dataset_name = "clearly-labelled-demo-interactions"
    fingerprint_payload = json.dumps(
        {
            "dataset": dataset_name,
            "products": products,
            "matrix": matrix.tolist(),
            "target": target,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    data_fingerprint = hashlib.sha256(fingerprint_payload.encode()).hexdigest()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    latest = session.scalar(
        select(RecommendationTrainingRun).order_by(RecommendationTrainingRun.created_at.desc())
    )
    if latest and latest.artifact_filename:
        latest_path = artifact_dir / latest.artifact_filename
        if latest_path.exists():
            latest_artifact = json.loads(latest_path.read_text(encoding="utf-8"))
            if latest_artifact.get("data_fingerprint") == data_fingerprint:
                return TrainingOutcome(run=latest, metadata=latest_artifact, changed=False)

    train = matrix.copy()
    held_out: list[tuple[int, int]] = []
    for user_index, row in enumerate(train):
        positive = np.flatnonzero(row)
        item_index = int(positive[-1])
        held_out.append((user_index, item_index))
        row[item_index] = 0
    component_count = max(1, min(3, min(train.shape) - 1))
    model = TruncatedSVD(n_components=component_count, random_state=42)
    user_factors = model.fit_transform(train)
    predictions = user_factors @ model.components_
    hits = 0
    failures: list[dict] = []
    requested_k = {"precision": 1, "balanced": 3, "recall": 5}[target]
    k = min(requested_k, len(products))
    for user_index, expected_item in held_out:
        predictions[user_index][train[user_index] > 0] = -np.inf
        top_items = np.argsort(predictions[user_index])[-k:][::-1]
        if expected_item in top_items:
            hits += 1
        else:
            failures.append(
                {
                    "demo_user": user_index,
                    "expected": products[expected_item],
                    "recommended": [products[int(item)] for item in top_items],
                }
            )
    precision = hits / (len(held_out) * k)
    recall = hits / len(held_out)
    metric_delta = {
        "precision": (
            round(precision - latest.precision_at_k, 4)
            if latest and latest.precision_at_k is not None
            else None
        ),
        "recall": (
            round(recall - latest.recall_at_k, 4)
            if latest and latest.recall_at_k is not None
            else None
        ),
    }
    run_id = str(uuid4())
    version = datetime.now(UTC).strftime("svd-%Y%m%d%H%M%S") + f"-{run_id[:6]}"
    artifact_filename = f"{version}.json"
    artifact = {
        "algorithm": "TruncatedSVD",
        "products": products,
        "components": model.components_.round(6).tolist(),
        "singular_values": model.singular_values_.round(6).tolist(),
        "precision_at_3": precision,
        "recall_at_3": recall,
        "dataset": dataset_name,
        "target": target,
        "k": k,
        "sample_count": int(matrix.shape[0]),
        "product_count": len(products),
        "data_fingerprint": data_fingerprint,
        "metric_delta": metric_delta,
    }
    (artifact_dir / artifact_filename).write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    training_run = RecommendationTrainingRun(
        id=run_id,
        version=version,
        status="succeeded",
        precision_at_k=precision,
        recall_at_k=recall,
        artifact_filename=artifact_filename,
        failure_examples=failures,
        finished_at=datetime.now(UTC),
    )
    session.add(training_run)
    session.commit()
    session.refresh(training_run)
    return TrainingOutcome(run=training_run, metadata=artifact, changed=True)
