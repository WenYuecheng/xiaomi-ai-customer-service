import unicodedata
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
    byte_length = len(value.encode("utf-8"))
    if not 8 <= byte_length <= 72:
        raise ValueError("密码长度必须为 8–72 个 UTF-8 字节")
    if not any(character.isalpha() for character in value) or not any(
        character.isdigit() for character in value
    ):
        raise ValueError("密码必须同时包含字母和数字")
    return value


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    avatar_key: AvatarKey | None = None

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not 1 <= len(normalized) <= 40:
            raise ValueError("显示名称必须为 1–40 个字符")
        if any(unicodedata.category(character).startswith("C") for character in normalized):
            raise ValueError("显示名称不能包含控制字符")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "ProfileUpdateRequest":
        if self.display_name is None and self.avatar_key is None:
            raise ValueError("至少需要修改一项资料")
        return self


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password: str
    new_password_confirm: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @model_validator(mode="after")
    def passwords_match(self) -> "ChangePasswordRequest":
        if self.new_password != self.new_password_confirm:
            raise ValueError("两次输入的新密码不一致")
        return self
