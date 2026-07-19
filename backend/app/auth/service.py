"""
文件职责：
该文件负责用户认证模块的核心业务逻辑，如用户创建、密码校验和身份验证。不涉及 HTTP 层和路由。

所属功能：
用户认证 -> 核心业务服务。

主要流程：
处理用户注册和登录的数据库级校验与数据持久化操作。

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

    Args:
        session (Session): SQLAlchemy 的同步数据库会话对象。
        username (str): 用户的注册用户名（将被转换为小写并去重）。
        password (str): 用户的注册明文密码（将被哈希）。
        role (str): 用户的初始角色（例如 'user', 'admin'）。

    Returns:
        User: 创建成功并持久化后的用户模型对象。

    Raises:
        ValueError: 如果用户名为空。
        AppError: 如果用户名已存在（HTTP 409 冲突）。
    """
    # 统一转换小写并去除首尾空格，保证一致性
    normalized = username.strip().lower()
    if not normalized:
        raise ValueError("username is required")

    # 查询数据库中是否已存在同名用户，防止重复注册
    if session.scalar(select(User).where(User.username == normalized)):
        raise AppError(409, "user_exists", "用户名已存在")

    # 构造新的用户实体，并对密码进行加密处理
    user = User(
        username=normalized,
        display_name=normalized,
        password_hash=hash_password(password),
        role=UserRole(role),
    )

    # 写入数据库并提交事务
    session.add(user)
    session.commit()

    # 刷新对象状态以获取数据库自动生成的字段（如主键 ID、创建时间等）
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

    Args:
        session (Session): 数据库会话。
        username (str): 登录提交的用户名。
        password (str): 登录提交的明文密码。

    Returns:
        User: 验证通过后的用户模型对象。

    异常：
    如果用户不存在、被禁用或密码错误，均抛出统一的 401 `AppError`，防止枚举账号泄露信息。
    """
    # 统一转换用户名大小写进行匹配
    user = session.scalar(select(User).where(User.username == username.strip().lower()))

    # 综合校验：用户是否存在、是否处于激活状态，以及密码验证是否通过
    # 注意：此处使用短路计算，如果 user 为 None，则不会调用 verify_password，防止异常
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise AppError(401, "invalid_credentials", "用户名或密码错误")

    return user
