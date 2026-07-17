from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth token type, not a credential


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime
