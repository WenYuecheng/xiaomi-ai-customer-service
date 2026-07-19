"""
文件职责：
该文件负责定义账号模块的 Pydantic 数据验证模型（Schemas）。

所属功能：
账号相关的数据输入校验、数据结构定义以及 API 响应格式化。

主要流程：
在 FastAPI 路由处理请求或响应时，通过此处定义的 Schema 自动对数据进行验证、序列化和反序列化。
"""

import unicodedata
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

AvatarKey = Literal[
    "aurora",
    "coral",
    "nebula",
    "ocean",
    "sunset",
    "mint",
    "cosmos",
    "ember",
]


def validate_password_strength(value: str) -> str:
    """
    验证密码强度是否符合系统要求。

    Args:
        value (str): 待验证的明文密码。

    Returns:
        str: 验证通过后的原密码。

    Raises:
        ValueError: 密码长度不符合要求，或未同时包含字母和数字时抛出。
    """
    byte_length = len(value.encode("utf-8"))
    # 检查密码的字节长度，必须在 8 到 72 之间（受 bcrypt 限制）
    if not 8 <= byte_length <= 72:
        raise ValueError("密码长度必须为 8–72 个 UTF-8 字节")
    # 检查是否同时包含字母和数字
    if not any(character.isalpha() for character in value) or not any(
        character.isdigit() for character in value
    ):
        raise ValueError("密码必须同时包含字母和数字")
    return value


class ProfileUpdateRequest(BaseModel):
    """
    生命周期：
    在处理用户更新个人资料请求（PATCH /profile）时被实例化和校验。

    职责：
    验证客户端提交的资料更新请求数据，包括显示名称和头像标识。

    重要属性：
    - display_name (str | None): 新的显示名称，可为空。
    - avatar_key (AvatarKey | None): 新的头像标识，必须为预定义的枚举值。
    """

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    avatar_key: AvatarKey | None = None

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        """
        验证显示名称字段。

        Args:
            value (str | None): 传入的显示名称。

        Returns:
            str | None: 去除首尾空格后的显示名称，或 None。

        Raises:
            ValueError: 长度不在 1-40 字符之间，或包含控制字符。
        """
        if value is None:
            return None
        normalized = value.strip()
        # 验证名称的实际字符长度
        if not 1 <= len(normalized) <= 40:
            raise ValueError("显示名称必须为 1–40 个字符")
        # 防止名称中包含不可见的控制字符（Category C）
        if any(unicodedata.category(character).startswith("C") for character in normalized):
            raise ValueError("显示名称不能包含控制字符")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "ProfileUpdateRequest":
        """
        在所有字段验证后，确保请求体中至少提供了一项修改内容。

        Returns:
            ProfileUpdateRequest: 当前模型实例。

        Raises:
            ValueError: 如果所有可修改字段均为 None。
        """
        # 避免无效的空更新请求，节约后续的数据库操作
        if self.display_name is None and self.avatar_key is None:
            raise ValueError("至少需要修改一项资料")
        return self


class ChangePasswordRequest(BaseModel):
    """
    生命周期：
    在处理用户修改密码请求（POST /change-password）时被实例化和校验。

    职责：
    验证密码修改请求所需的数据，并确保新旧密码逻辑和复杂度合法。

    重要属性：
    - current_password (str): 用户当前的明文密码。
    - new_password (str): 用户期望修改的新密码。
    - new_password_confirm (str): 新密码的二次确认输入。
    """

    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password: str
    new_password_confirm: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        """
        验证新密码是否符合强度要求。

        Args:
            value (str): 传入的新密码。

        Returns:
            str: 验证通过后的新密码。

        Raises:
            ValueError: 密码强度不达标。
        """
        return validate_password_strength(value)

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordRequest":
        """
        在所有字段验证后，检查新密码与确认密码是否一致。

        Returns:
            ChangePasswordRequest: 当前模型实例。

        Raises:
            ValueError: 如果两次输入的新密码不匹配。
        """
        if self.new_password != self.new_password_confirm:
            raise ValueError("两次输入的新密码不一致")
        return self


class AccountStats(BaseModel):
    """
    生命周期：
    在生成用户仪表盘响应时被实例化。

    职责：
    封装与用户账户相关的各项统计数据。

    重要属性：
    - consultation_count (int): 用户的咨询（聊天）总次数。
    - advisor_plan_count (int): 用户获取顾问计划的总次数。
    - feedback_count (int): 用户提交的反馈总次数。
    - helpful_rate (int | None): 用户反馈被标记为“有帮助”的百分比。
    """

    consultation_count: int
    advisor_plan_count: int
    feedback_count: int
    helpful_rate: int | None


class InterestSummary(BaseModel):
    """
    生命周期：
    在生成用户仪表盘响应时，基于分析结果生成并被实例化。

    职责：
    表示用户的偏好和兴趣摘要。

    重要属性：
    - product_preferences (list[str]): 用户倾向的产品偏好列表。
    - intent_distribution (dict[str, int]): 用户各种意图的分布统计。
    """

    product_preferences: list[str]
    intent_distribution: dict[str, int]


class ActivityTrendPoint(BaseModel):
    """
    生命周期：
    在生成用户仪表盘响应时被用于构建趋势图数据点。

    职责：
    表示指定日期的活动发生次数。

    重要属性：
    - date (date): 统计的日期。
    - count (int): 该日期的活动总数。
    """

    date: date
    count: int


class AccountActivity(BaseModel):
    """
    生命周期：
    在从数据库提取用户交互历史、并转换为统一活动列表展示时被实例化。

    职责：
    标准化描述用户的单次活动，供前端列表呈现。

    重要属性：
    - id (str): 带有活动类型前缀的唯一标识（如 chat:xxx）。
    - type (Literal): 活动类型（chat/advisor/feedback）。
    - title (str): 活动的主题或简要标题。
    - summary (str): 活动内容的摘要截取。
    - occurred_at (datetime): 活动发生的时间戳。
    - resource_id (str): 关联的底层资源（如对话记录）的 ID。
    """

    id: str
    type: Literal["chat", "advisor", "feedback"]
    title: str
    summary: str
    occurred_at: datetime
    resource_id: str


class ActivityListResponse(BaseModel):
    """
    生命周期：
    在处理获取活动列表请求（GET /activities）完毕，封装分页结果时被实例化。

    职责：
    定义分页返回给客户端的用户活动列表数据结构。

    重要属性：
    - items (list[AccountActivity]): 当前页的活动条目列表。
    - next_cursor (str | None): 获取下一页数据的游标标识；无下一页时为 None。
    """

    items: list[AccountActivity]
    next_cursor: str | None


class AccountDashboardResponse(BaseModel):
    """
    生命周期：
    在处理获取用户仪表盘数据请求（GET /dashboard）完毕时被实例化。

    职责：
    聚合用户的各项宏观数据，用于个人中心首页展示。

    重要属性：
    - stats (AccountStats): 用户行为的统计概览。
    - joined_days (int): 用户加入的天数。
    - growth_level (int): 根据活跃度计算的用户成长等级。
    - interests (InterestSummary): 用户的兴趣和偏好特征。
    - trend (list[ActivityTrendPoint]): 近期的活动趋势数据（用于图表）。
    - recent_activities (list[AccountActivity]): 用户最近参与的若干活动。
    """

    stats: AccountStats
    joined_days: int
    growth_level: int
    interests: InterestSummary
    trend: list[ActivityTrendPoint]
    recent_activities: list[AccountActivity]
