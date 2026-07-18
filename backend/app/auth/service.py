"""
文件职责：
负责用户认证模块的核心业务逻辑，如用户创建、密码校验和身份验证。不涉及 HTTP 层和路由。

所属功能：
用户认证 -> 核心业务服务。

主要依赖：
- SQLAlchemy Session 进行数据库查询。
- `app.auth.security` 提供密码哈希与校验能力。
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.core.errors import AppError
from app.db.models import User, UserRole


def create_user(session: Session, username: str, password: str, role: str) -> User:
    """
    功能归属：
    用户认证 -> 用户注册/创建。

    函数职责：
    在数据库中创建新用户记录。确保用户名不重复并对密码进行哈希加密。

    副作用：
    写入数据库。
    """
    normalized = username.strip().lower()
    if not normalized:
        raise ValueError("username is required")
    if session.scalar(select(User).where(User.username == normalized)):
        raise AppError(409, "user_exists", "用户名已存在")
    user = User(
        username=normalized,
        display_name=normalized,
        password_hash=hash_password(password),
        role=UserRole(role),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate(session: Session, username: str, password: str) -> User:
    """
    功能归属：
    用户认证 -> 登录鉴权。

    函数职责：
    校验用户提供的账号密码是否正确，以及账号是否处于激活状态。

    调用方：
    主要是 `app.auth.router.login` 路由。

    异常：
    如果用户不存在、被禁用或密码错误，均抛出统一的 401 `AppError`，防止枚举账号泄露信息。
    """
    # 统一转换用户名大小写进行匹配
    user = session.scalar(select(User).where(User.username == username.strip().lower()))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise AppError(401, "invalid_credentials", "用户名或密码错误")
    return user
