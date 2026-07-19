"""
文件职责：
处理用户对话行为的统计分析。基于行为日志（BehaviorEvent）提炼出热词、用户意图分布。

所属功能：
运营分析与推荐 -> 统计分析服务。

主要流程：
1. `hot_topics`: 根据给定时间窗口查询对话日志，利用时间衰减提取并计算产品型号及名词的热度。
2. `hot_topic_heatmap`: 统计每天的交互次数，提供时间序列热力图数据。
3. `build_user_profile`: 聚合特定用户的偏好、意图及反馈信息。
"""

from collections import Counter
from datetime import UTC, datetime, timedelta

import jieba
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import BehaviorEvent, Feedback
from app.ingestion.parsers import extract_product_models
from app.operations.schemas import HotTopic, HotTopicHeatCell, UserProfileResponse

STOP_WORDS = {"什么", "怎么", "怎么样", "是否", "可以", "支持", "一下", "这个", "那个"}


def time_boundary(window: str) -> datetime:
    """
    内部辅助函数：根据查询窗口名称返回过滤的起始时间。

    Args:
        window: 时间窗口，支持 "day", "week", "month"。

    Returns:
        计算得出的起算时间点（datetime）。
    """
    delta = {"day": timedelta(days=1), "week": timedelta(days=7), "month": timedelta(days=30)}[
        window
    ]
    return datetime.now(UTC) - delta


def hot_topics(session: Session, window: str) -> list[HotTopic]:
    """
    基于时间衰减权重的热词统计算法。

    执行链：
    1. 获取指定时间窗口（如最近7天）的聊天日志。
    2. 基于距离现在的时间长短计算权重衰减（越近发生的权重越高，公式：1 / (1 + age_hours / 24)）。
    3. 提取用户提问中的具体产品型号（极高优先级）以及利用 jieba 拆分出来的专有名词。
    4. 汇总得分并返回 Top 20 热词。

    Args:
        session: 数据库会话。
        window: "day" | "week" | "month"。

    Returns:
        按热度得分从高到低排序的热词对象列表。
    """
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


def hot_topic_heatmap(session: Session, window: str) -> list[HotTopicHeatCell]:
    events = list(
        session.scalars(
            select(BehaviorEvent).where(
                BehaviorEvent.event_type == "chat",
                BehaviorEvent.created_at >= time_boundary(window),
            )
        )
    )
    counts: Counter[str] = Counter(event.created_at.date().isoformat() for event in events)
    return [HotTopicHeatCell(date=date, count=count) for date, count in sorted(counts.items())]


def build_user_profile(session: Session, user_id: str) -> UserProfileResponse:
    """
    聚合汇总指定用户的对话画像。

    主要职责：
    基于单个用户的历史 BehaviorEvent，统计其最关心的产品 Top 10、
    意图触发的分布（如查了几次物流，咨询了几次故障）及对机器人的评价反馈分布。

    Args:
        session: 数据库会话。
        user_id: 需要查询画像的目标用户 ID。

    Returns:
        包含用户喜好、意图统计、点赞反馈数目的画像响应对象。
    """
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
