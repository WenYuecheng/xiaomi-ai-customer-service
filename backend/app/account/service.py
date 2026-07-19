"""
文件职责：
该文件负责账号模块的核心业务逻辑处理。

所属功能：
账号数据管理，包括个人资料更新、密码修改、活动流水收集与分页、以及个人主页仪表盘数据的聚合。

主要流程：
接收来自 Router 层的合法请求载荷，结合数据库会话执行数据存取和转换操作，
最终将加工后的结果返回给 Router。
"""

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
    """
    更新用户的个人资料并记录审计事件。

    Args:
        session (Session): 数据库会话。
        user (User): 当前需更新的数据库用户对象。
        payload (ProfileUpdateRequest): 包含需更新资料的数据载荷。

    Returns:
        User: 更新后的用户对象。

    Raises:
        无特定异常。
    """
    changed_fields: list[str] = []

    # 逐一比较并应用显示名称的更改，若发生变化则计入变更字段列表
    if payload.display_name is not None and payload.display_name != user.display_name:
        user.display_name = payload.display_name
        changed_fields.append("display_name")

    # 逐一比较并应用头像的更改
    if payload.avatar_key is not None and payload.avatar_key != user.avatar_key:
        user.avatar_key = payload.avatar_key
        changed_fields.append("avatar_key")

    # 如果检测到任何字段发生了实际变化，则同时插入一条行为事件（BehaviorEvent）用作审计追踪
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
    """
    修改用户密码并使当前 Token 版本失效。

    Args:
        session (Session): 数据库会话。
        user (User): 当前需更新的数据库用户对象。
        payload (ChangePasswordRequest): 包含新旧密码的数据载荷。

    Returns:
        None

    Raises:
        AppError: 当提供的当前密码无法通过校验时，抛出 400 异常。
    """
    # 验证用户提供的“当前密码”是否正确，防范越权或 CSRF 类攻击
    if not verify_password(payload.current_password, user.password_hash):
        raise AppError(400, "invalid_current_password", "当前密码不正确")

    # 更新密码哈希，并递增 token_version 以立即使该用户目前所有的 JWT 令牌失效
    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    session.add(user)

    # 记录修改密码的审计事件
    session.add(
        BehaviorEvent(
            user_id=user.id,
            event_type="audit:account:password_changed",
            payload={"action": "password_changed"},
        )
    )
    session.commit()


def _summary(value: str, limit: int = 140) -> str:
    """
    对给定的字符串内容进行压缩和截断，以用作摘要显示。

    Args:
        value (str): 原始长文本。
        limit (int): 截断的长度限制，默认为 140。

    Returns:
        str: 清理了冗余空白符并截断至指定长度后的摘要文本，如果发生了截断，末尾将添加省略号。

    Raises:
        无特定异常。
    """
    # 压缩文本中的多个空白字符为一个空格，使排版更紧凑
    compact = " ".join(value.split())
    return compact if len(compact) <= limit else f"{compact[: limit - 1]}…"


def collect_activities(session: Session, user_id: str) -> list[AccountActivity]:
    """
    全量收集指定用户的所有交互历史（聊天、顾问交互、反馈评估），并标准化为列表。

    Args:
        session (Session): 数据库会话。
        user_id (str): 目标用户的唯一 ID。

    Returns:
        list[AccountActivity]: 按发生时间降序排列的统一格式的活动记录列表。

    Raises:
        无特定异常。
    """
    activities: list[AccountActivity] = []

    # === 1. 收集普通对话（chat）活动 ===
    # 联表查询 Conversation 与其下的 Message，筛选出该用户的所有发言（MessageRole.user）
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

    # === 2. 收集顾问计划（advisor）活动 ===
    # 查询状态为已完成的 AdvisorTurn 记录
    advisor_rows = session.execute(
        select(AdvisorTurn, AdvisorSession)
        .join(AdvisorSession, AdvisorTurn.session_id == AdvisorSession.id)
        .where(AdvisorSession.user_id == user_id, AdvisorTurn.status == "completed")
    ).all()

    for turn, advisor_session in advisor_rows:
        # 提取推荐建议或回退使用提问原文作为活动摘要
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

    # === 3. 收集评价反馈（feedback）活动 ===
    # 联表获取该用户关联的所有反馈记录
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
            # 根据用户的评分选择展示对应的操作类型文本
            title="标记为有帮助" if feedback.rating == FeedbackRating.up else "提交改进反馈",
            summary=_summary(feedback.correction or "感谢你的反馈，系统已记录这次评价。"),
            occurred_at=feedback.updated_at or feedback.created_at,
            resource_id=conversation.id,
        )
        for feedback, _message, conversation in feedback_rows
    )

    # 将所有异构活动按发生时间倒序排列；时间一致时使用 ID 排序，保证结果稳定。
    return sorted(activities, key=lambda item: (item.occurred_at, item.id), reverse=True)


def paginate_activities(
    activities: list[AccountActivity],
    cursor: str | None,
    limit: int,
) -> ActivityListResponse:
    """
    对收集到的全量活动列表进行游标分页处理。

    Args:
        activities (list[AccountActivity]): 已根据时间排序的完整活动列表。
        cursor (str | None): base64 编码的上一页最后一条记录的 ID，若为空则从第一条开始。
        limit (int): 本次请求允许返回的最大条数。

    Returns:
        ActivityListResponse: 切片后的列表与计算出的下一页游标。

    Raises:
        AppError: 提供游标格式不合法，或列表中无法找到该游标对应项时。
    """
    start = 0
    if cursor:
        try:
            # 解码前端传递的安全 base64 游标并尝试在列表中定位到此 ID
            cursor_id = urlsafe_b64decode(cursor.encode()).decode()
            # 从游标对应记录的下一个位置开始截取
            start = next(index + 1 for index, item in enumerate(activities) if item.id == cursor_id)
        except (ValueError, UnicodeError, StopIteration) as exc:
            # 解析异常或列表中找不到游标时抛出特定业务错误
            raise AppError(422, "invalid_cursor", "活动游标无效") from exc

    # 执行列表切片，获取当前页的数据
    items = activities[start : start + limit]
    has_more = start + limit < len(activities)

    # 如果还有下一页数据，选取当前页最后一条数据的 ID 进行 base64 编码生成新的游标
    next_cursor = urlsafe_b64encode(items[-1].id.encode()).decode() if items and has_more else None

    return ActivityListResponse(items=items, next_cursor=next_cursor)


def account_dashboard(session: Session, user: User) -> AccountDashboardResponse:
    """
    整合并计算个人仪表盘所需的全部统计与图表数据。

    Args:
        session (Session): 数据库会话。
        user (User): 当前用户对象。

    Returns:
        AccountDashboardResponse: 封装好的完整仪表盘数据结构。

    Raises:
        无特定异常。
    """
    # 1. 提取全量活动流并按类型统计总次数
    activities = collect_activities(session, user.id)
    counts = Counter(item.type for item in activities)

    # 2. 查询并统计好评占比
    feedback = list(session.scalars(select(Feedback).where(Feedback.user_id == user.id)))
    helpful_count = sum(item.rating == FeedbackRating.up for item in feedback)
    helpful_rate = round(helpful_count / len(feedback) * 100) if feedback else None

    # 3. 提取用户画像中的产品偏好与意图分布
    profile = build_user_profile(session, user.id)

    # 4. 生成最近 14 天的活动趋势图表数据
    today = datetime.now(UTC).date()
    # 过滤并统计属于最近 14 天的活动数量
    trend_counts = Counter(
        item.occurred_at.date()
        for item in activities
        if item.occurred_at.date() >= today - timedelta(days=13)
    )

    # 5. 基于总体活跃度（三类活动之和）计算成长等级逻辑
    interaction_count = counts["chat"] + counts["advisor"] + counts["feedback"]
    growth_level = 1 if interaction_count < 5 else 2 if interaction_count < 15 else 3
    if interaction_count >= 40:
        growth_level = 4

    joined_date: date = user.created_at.date()

    # 组合为视图响应对象并返回
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
