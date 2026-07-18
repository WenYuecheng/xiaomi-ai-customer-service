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
