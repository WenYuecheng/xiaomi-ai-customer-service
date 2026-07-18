"""
文件职责：
定义用户认证模块的输入与输出数据传输对象（DTO），用于 HTTP 接口参数校验和响应序列化。

所属功能：
用户认证 -> 视图模型/DTO。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

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
    role: UserRole
    is_active: bool
    created_at: datetime
