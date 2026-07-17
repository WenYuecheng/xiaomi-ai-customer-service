from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import Settings
from app.core.errors import AppError


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > 72:
        raise ValueError("password must not exceed 72 UTF-8 bytes")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, UnicodeError):
        return False


def create_access_token(subject: str, role: str, settings: Settings) -> str:
    if not settings.jwt_secret or len(settings.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 characters")
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "iss": settings.app_name,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict:
    if not settings.jwt_secret:
        raise AppError(401, "invalid_token", "登录凭证无效")
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.app_name,
            options={"require": ["sub", "exp", "iat", "iss"]},
        )
    except jwt.PyJWTError as exc:
        raise AppError(401, "invalid_token", "登录凭证无效或已过期") from exc

