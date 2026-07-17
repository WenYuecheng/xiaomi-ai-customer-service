from collections import Counter
from datetime import UTC, datetime, timedelta

import jieba
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BehaviorEvent, Feedback
from app.ingestion.parsers import extract_product_models
from app.operations.schemas import HotTopic, UserProfileResponse

STOP_WORDS = {"什么", "怎么", "怎么样", "是否", "可以", "支持", "一下", "这个", "那个"}


def time_boundary(window: str) -> datetime:
    delta = {"day": timedelta(days=1), "week": timedelta(days=7), "month": timedelta(days=30)}[
        window
    ]
    return datetime.now(UTC) - delta


def hot_topics(session: Session, window: str) -> list[HotTopic]:
    events = list(
        session.scalars(
            select(BehaviorEvent).where(
                BehaviorEvent.event_type == "chat",
                BehaviorEvent.created_at >= time_boundary(window),
            )
        )
    )
    counter: Counter[str] = Counter()
    now = datetime.now(UTC)
    for event in events:
        question = str(event.payload.get("question", ""))
        age_hours = max(0.0, (now - event.created_at.replace(tzinfo=UTC)).total_seconds() / 3600)
        weight = 1 / (1 + age_hours / 24)
        terms = set(extract_product_models(question))
        terms.update(
            token.strip()
            for token in jieba.cut(question)
            if len(token.strip()) >= 2 and token.strip() not in STOP_WORDS
        )
        for term in terms:
            counter[term] += weight
    return [
        HotTopic(term=term, count=round(score), score=round(score, 4))
        for term, score in counter.most_common(20)
    ]


def build_user_profile(session: Session, user_id: str) -> UserProfileResponse:
    events = list(
        session.scalars(
            select(BehaviorEvent)
            .where(BehaviorEvent.user_id == user_id)
            .order_by(BehaviorEvent.created_at)
        )
    )
    product_counts: Counter[str] = Counter()
    intent_counts: Counter[str] = Counter()
    for event in events:
        if event.event_type != "chat":
            continue
        product_counts.update(extract_product_models(str(event.payload.get("question", ""))))
        intent = event.payload.get("intent")
        if intent:
            intent_counts[str(intent)] += 1
    feedback_counts = Counter(
        item.rating.value
        for item in session.scalars(select(Feedback).where(Feedback.user_id == user_id))
    )
    return UserProfileResponse(
        user_id=user_id,
        product_preferences=[item for item, _ in product_counts.most_common(10)],
        intent_distribution=dict(intent_counts),
        feedback_summary=dict(feedback_counts),
        event_count=len(events),
    )
