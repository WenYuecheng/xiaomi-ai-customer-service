"""
文件职责：
该文件负责提供 FastAPI 路由所需的鉴权依赖（Dependencies），实现请求级的权限控制。

所属功能：
用户认证 -> 鉴权与权限控制。

主要流程：
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

    Args:
        request (Request): FastAPI 的请求对象，用于获取全局配置等。
        session (SessionDep): 数据库会话依赖，用于执行数据库查询。
        token (str): 提取出的 OAuth2 Token 字符串。

    Returns:
        User: 当前请求对应的合法数据库 User 对象。

    Raises:
        AppError: 当 Token 无效、用户不存在、用户已停用或 Token 版本不匹配时抛出 401 异常。
    """
    # 步骤 1：解析访问令牌获取 Payload 信息
    payload = decode_access_token(token, request.app.state.settings)

    # 步骤 2：根据 Payload 中的用户 ID (sub) 在数据库中查询对应用户
    user = session.get(User, payload["sub"])

    # 步骤 3：验证用户记录是否存在以及是否处于激活状态（防止禁用用户继续访问）
    if not user or not user.is_active:
        raise AppError(401, "invalid_token", "用户不存在或已停用")

    # 步骤 4：验证 Token 中的版本号是否与数据库中的版本号一致，用于实现强制下线等功能
    if int(payload.get("ver", 0)) != user.token_version:
        raise AppError(401, "invalid_token", "登录凭证已失效，请重新登录")

    return user


# 定义可复用的依赖类型，路由只需声明参数类型即可自动触发注入
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable:
    """
    函数职责：
    构造一个角色校验的依赖函数，用于限制特定路由的访问权限。

    Args:
        *roles (UserRole): 允许访问该路由的一个或多个用户角色。

    Returns:
        Callable: 供 FastAPI Depends 使用的内部依赖函数。
    """
    allowed = set(roles)

    def dependency(current_user: CurrentUserDep) -> User:
        """
        内部依赖函数，执行具体的角色验证。

        Args:
            current_user (User): 已通过基本鉴权的当前用户对象。

        Returns:
            User: 验证通过后的用户对象。

        Raises:
            AppError: 当用户角色不在允许的角色集合中时，抛出 403 异常。
        """
        # 判断当前用户的角色是否在允许的角色集合中，如果没有则拒绝访问
        if current_user.role not in allowed:
            raise AppError(403, "forbidden", "没有执行此操作的权限")
        return current_user

    return dependency


AdminOrOperatorDep = Annotated[
    User,
    Depends(require_roles(UserRole.admin, UserRole.operator)),
]
