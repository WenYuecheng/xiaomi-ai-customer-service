from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from app.auth.security import decode_access_token
from app.core.errors import AppError
from app.db.base import SessionDep
from app.db.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    request: Request,
    session: SessionDep,
    token: str = Depends(oauth2_scheme),
) -> User:
    payload = decode_access_token(token, request.app.state.settings)
    user = session.get(User, payload["sub"])
    if not user or not user.is_active:
        raise AppError(401, "invalid_token", "用户不存在或已停用")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable:
    allowed = set(roles)

    def dependency(current_user: CurrentUserDep) -> User:
        if current_user.role not in allowed:
            raise AppError(403, "forbidden", "没有执行此操作的权限")
        return current_user

    return dependency


AdminOrOperatorDep = Annotated[
    User,
    Depends(require_roles(UserRole.admin, UserRole.operator)),
]
