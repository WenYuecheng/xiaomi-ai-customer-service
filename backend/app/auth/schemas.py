"""
文件职责：
该文件负责定义用户认证模块的输入与输出数据传输对象（DTO），用于 HTTP 接口参数校验和响应序列化。

所属功能：
用户认证 -> 视图模型/DTO。

主要流程：
无复杂流程，主要通过 Pydantic 模型对请求体和响应体进行结构化定义和数据校验。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.account.schemas import validate_password_strength
from app.db.models import UserRole


class TokenResponse(BaseModel):
    """
    类职责：
    登录成功后返回给客户端的令牌响应体，符合 OAuth2 规范格式。

    生命周期：
    在每次成功登录或注册后实例化并返回给客户端。

    重要属性：
    - access_token: JWT 格式的访问令牌字符串。
    - token_type: 固定为 "bearer"。
    """

    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth token type, not a credential


class UserResponse(BaseModel):
    """
    类职责：
    获取用户信息接口返回的数据结构。过滤了密码哈希等敏感字段。

    生命周期：
    在请求 `/me` 或注册成功后实例化。

    重要属性：
    - id, username, display_name, avatar_key, role, is_active, created_at
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    display_name: str
    avatar_key: str
    role: UserRole
    is_active: bool
    created_at: datetime


class RegisterRequest(BaseModel):
    """
    类职责：
    接收并校验用户注册请求的参数。

    重要验证规则：
    - username: 3到32位字母、数字或下划线。
    - password: 需要满足一定的强度要求。
    - password_confirm: 必须与 password 一致。
    """

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=40)
    password: str
    password_confirm: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        """
        验证用户名格式，去除首尾空格并转换为小写。

        Args:
            value (str): 用户输入的原始用户名。

        Returns:
            str: 格式化后的用户名。

        Raises:
            ValueError: 如果格式不符合要求。
        """
        # 转小写并去空格，防止仅大小写不同的同名用户注册
        normalized = value.strip().lower()

        # 校验长度及允许的字符类型：仅限 ASCII 字母、数字和下划线
        if not 3 <= len(normalized) <= 32 or not all(
            character.isascii() and (character.isalnum() or character == "_")
            for character in normalized
        ):
            raise ValueError("用户名只能包含 3–32 位字母、数字和下划线")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """
        验证密码强度。复用 account 模块的密码验证逻辑。
        """
        return validate_password_strength(value)

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        """
        模型级别的验证器：检查两次输入的密码是否一致。
        """
        # 判断确认密码是否与密码一致，防止用户输错
        if self.password != self.password_confirm:
            raise ValueError("两次输入的密码不一致")
        return self


class AuthSessionResponse(TokenResponse):
    """
    类职责：
    包含 Token 响应与用户详细信息的聚合体。主要用于注册成功后，一次性下发凭证和用户信息。
    """

    user: UserResponse
