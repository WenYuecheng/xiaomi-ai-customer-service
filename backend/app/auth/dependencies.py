"""
文件职责：
提供 FastAPI 路由所需的鉴权依赖（Dependencies），实现请求级的权限控制。

所属功能：
用户认证 -> 鉴权与权限控制。

主要机制：
通过 FastAPI 的 `Depends` 机制，在进入具体的路由函数之前，提取请求头中的 Token，
解析并查询对应的数据库用户记录，确保访问者身份合法，并拦截未授权请求。
"""

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
    """
    功能归属：
    用户认证 -> 鉴权。

    函数职责：
    1. 提取 Authorization Header 中的 Bearer Token。
    2. 解析并验证 JWT 的合法性。
    3. 根据 Payload 中的 sub (用户 ID) 查询数据库，并校验账号状态。

    返回值：
    返回当前合法的数据库 User 对象。供路由函数使用。
    """
    payload = decode_access_token(token, request.app.state.settings)
    user = session.get(User, payload["sub"])
    if not user or not user.is_active:
        raise AppError(401, "invalid_token", "用户不存在或已停用")
    return user


# 定义可复用的依赖类型，路由只需声明参数类型即可自动触发注入
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
