from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import hash_password, verify_password
from app.core.errors import AppError
from app.db.models import User, UserRole


def create_user(session: Session, username: str, password: str, role: str) -> User:
    normalized = username.strip().lower()
    if not normalized:
        raise ValueError("username is required")
    if session.scalar(select(User).where(User.username == normalized)):
        raise AppError(409, "user_exists", "用户名已存在")
    user = User(
        username=normalized,
        password_hash=hash_password(password),
        role=UserRole(role),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate(session: Session, username: str, password: str) -> User:
    user = session.scalar(select(User).where(User.username == username.strip().lower()))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        raise AppError(401, "invalid_credentials", "用户名或密码错误")
    return user
