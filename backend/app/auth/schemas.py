"""
文件职责：
定义用户认证模块的输入与输出数据传输对象（DTO），用于 HTTP 接口参数校验和响应序列化。

所属功能：
用户认证 -> 视图模型/DTO。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.account.schemas import validate_password_strength
from app.db.models import UserRole


class TokenResponse(BaseModel):
    """
    登录成功后返回给客户端的令牌响应体，符合 OAuth2 规范格式。
    """

    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth token type, not a credential


class UserResponse(BaseModel):
    """
    获取用户信息接口返回的数据结构。过滤了密码哈希等敏感字段。
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
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=40)
    password: str
    password_confirm: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not 3 <= len(normalized) <= 32 or not all(
            character.isascii() and (character.isalnum() or character == "_")
            for character in normalized
        ):
            raise ValueError("用户名只能包含 3–32 位字母、数字和下划线")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.password_confirm:
            raise ValueError("两次输入的密码不一致")
        return self


class AuthSessionResponse(TokenResponse):
    user: UserResponse
