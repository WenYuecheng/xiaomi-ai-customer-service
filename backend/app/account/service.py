from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections import Counter
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.account.schemas import (
    AccountActivity,
    AccountDashboardResponse,
    AccountStats,
    ActivityListResponse,
    ActivityTrendPoint,
    ChangePasswordRequest,
    InterestSummary,
    ProfileUpdateRequest,
)
from app.auth.security import hash_password, verify_password
from app.core.errors import AppError
from app.db.models import (
    AdvisorSession,
    AdvisorTurn,
    BehaviorEvent,
    Conversation,
    Feedback,
    FeedbackRating,
    Message,
    MessageRole,
    User,
)
from app.operations.analytics import build_user_profile


def update_profile(session: Session, user: User, payload: ProfileUpdateRequest) -> User:
    changed_fields: list[str] = []
    if payload.display_name is not None and payload.display_name != user.display_name:
        user.display_name = payload.display_name
        changed_fields.append("display_name")
    if payload.avatar_key is not None and payload.avatar_key != user.avatar_key:
        user.avatar_key = payload.avatar_key
        changed_fields.append("avatar_key")
    if changed_fields:
        session.add(
            BehaviorEvent(
                user_id=user.id,
                event_type="audit:account:profile_updated",
                payload={"changed_fields": changed_fields},
            )
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def change_password(session: Session, user: User, payload: ChangePasswordRequest) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise AppError(400, "invalid_current_password", "当前密码不正确")
    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    session.add(user)
    session.add(
        BehaviorEvent(
            user_id=user.id,
            event_type="audit:account:password_changed",
            payload={"action": "password_changed"},
        )
    )
    session.commit()


def _summary(value: str, limit: int = 140) -> str:
    compact = " ".join(value.split())
    return compact if len(compact) <= limit else f"{compact[: limit - 1]}…"


def collect_activities(session: Session, user_id: str) -> list[AccountActivity]:
    activities: list[AccountActivity] = []
    chat_rows = session.execute(
        select(Message, Conversation)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == user_id, Message.role == MessageRole.user)
    ).all()
    activities.extend(
        AccountActivity(
            id=f"chat:{message.id}",
            type="chat",
            title="可信问答",
            summary=_summary(message.content),
            occurred_at=message.created_at,
            resource_id=conversation.id,
        )
        for message, conversation in chat_rows
    )
    advisor_rows = session.execute(
        select(AdvisorTurn, AdvisorSession)
        .join(AdvisorSession, AdvisorTurn.session_id == AdvisorSession.id)
        .where(AdvisorSession.user_id == user_id, AdvisorTurn.status == "completed")
    ).all()
    for turn, advisor_session in advisor_rows:
        recommendation = (turn.plan or {}).get("recommendation", {})
        activities.append(
            AccountActivity(
                id=f"advisor:{turn.id}",
                type="advisor",
                title=advisor_session.title,
                summary=_summary(str(recommendation.get("summary") or turn.question)),
                occurred_at=turn.created_at,
                resource_id=advisor_session.id,
            )
        )
    feedback_rows = session.execute(
        select(Feedback, Message, Conversation)
        .join(Message, Feedback.message_id == Message.id)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Feedback.user_id == user_id, Conversation.user_id == user_id)
    ).all()
    activities.extend(
        AccountActivity(
            id=f"feedback:{feedback.id}",
            type="feedback",
            title="标记为有帮助" if feedback.rating == FeedbackRating.up else "提交改进反馈",
            summary=_summary(feedback.correction or "感谢你的反馈，系统已记录这次评价。"),
            occurred_at=feedback.updated_at or feedback.created_at,
            resource_id=conversation.id,
        )
        for feedback, _message, conversation in feedback_rows
    )
    return sorted(activities, key=lambda item: (item.occurred_at, item.id), reverse=True)


def paginate_activities(
    activities: list[AccountActivity],
    cursor: str | None,
    limit: int,
) -> ActivityListResponse:
    start = 0
    if cursor:
        try:
            cursor_id = urlsafe_b64decode(cursor.encode()).decode()
            start = next(index + 1 for index, item in enumerate(activities) if item.id == cursor_id)
        except (ValueError, UnicodeError, StopIteration) as exc:
            raise AppError(422, "invalid_cursor", "活动游标无效") from exc
    items = activities[start : start + limit]
    has_more = start + limit < len(activities)
    next_cursor = urlsafe_b64encode(items[-1].id.encode()).decode() if items and has_more else None
    return ActivityListResponse(items=items, next_cursor=next_cursor)


def account_dashboard(session: Session, user: User) -> AccountDashboardResponse:
    activities = collect_activities(session, user.id)
    counts = Counter(item.type for item in activities)
    feedback = list(session.scalars(select(Feedback).where(Feedback.user_id == user.id)))
    helpful_count = sum(item.rating == FeedbackRating.up for item in feedback)
    helpful_rate = round(helpful_count / len(feedback) * 100) if feedback else None
    profile = build_user_profile(session, user.id)
    today = datetime.now(UTC).date()
    trend_counts = Counter(
        item.occurred_at.date()
        for item in activities
        if item.occurred_at.date() >= today - timedelta(days=13)
    )
    interaction_count = counts["chat"] + counts["advisor"] + counts["feedback"]
    growth_level = 1 if interaction_count < 5 else 2 if interaction_count < 15 else 3
    if interaction_count >= 40:
        growth_level = 4
    joined_date: date = user.created_at.date()
    return AccountDashboardResponse(
        stats=AccountStats(
            consultation_count=counts["chat"],
            advisor_plan_count=counts["advisor"],
            feedback_count=counts["feedback"],
            helpful_rate=helpful_rate,
        ),
        joined_days=max(1, (today - joined_date).days + 1),
        growth_level=growth_level,
        interests=InterestSummary(
            product_preferences=profile.product_preferences,
            intent_distribution=profile.intent_distribution,
        ),
        trend=[
            ActivityTrendPoint(
                date=today - timedelta(days=offset),
                count=trend_counts[today - timedelta(days=offset)],
            )
            for offset in range(13, -1, -1)
        ],
        recent_activities=activities[:5],
    )
