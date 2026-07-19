"""
文件职责：
该文件负责封装用户密码的哈希加密与校验，以及 JWT (JSON Web Token) 的签发与解析。

所属功能：
用户认证 -> 安全与凭证管理。

主要流程：
1. 密码散列：使用 bcrypt 算法对明文密码进行单向哈希，防止数据库泄露导致密码明文暴露。
2. 令牌签发：用户登录成功后，使用系统配置的 JWT_SECRET 生成短期有效的 JWT 访问令牌。
3. 令牌校验：解析请求头携带的 JWT，验证签名有效性、是否过期以及提取用户标识（sub）。

依赖：
bcrypt, PyJWT。
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import Settings
from app.core.errors import AppError


def hash_password(password: str) -> str:
    """
    功能归属：
    用户认证 -> 安全与凭证管理。

    函数职责：
    对明文密码进行不可逆散列加密，用于新用户注册或修改密码时保存到数据库。

    调用方：
    `app.auth.service.create_user` 等。

    Args:
        password (str): 用户输入的明文密码。

    Returns:
        str: 使用 bcrypt 加密后的哈希字符串。

    Raises:
        ValueError: 如果密码字节长度超过 72 字节（bcrypt 限制）。
    """
    raw = password.encode("utf-8")
    if len(raw) > 72:
        raise ValueError("password must not exceed 72 UTF-8 bytes")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """
    功能归属：
    用户认证 -> 密码校验。

    函数职责：
    验证用户登录时提交的明文密码与数据库保存的散列值是否匹配。

    调用方：
    `app.auth.service.authenticate`。

    Args:
        password (str): 用户输入的明文密码。
        password_hash (str): 数据库中保存的哈希字符串。

    Returns:
        bool: 匹配返回 True，否则返回 False。

    异常：
    如果 bcrypt 校验遇到非法的输入，捕获异常并返回 False。
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, UnicodeError):
        return False


def create_access_token(
    subject: str,
    role: str,
    settings: Settings,
    token_version: int = 0,
) -> str:
    """
    功能归属：
    用户认证 -> 令牌生成。

    函数职责：
    生成符合 JWT 规范的登录令牌。

    流程位置：
    在 `login` 或 `register` 成功后被调用。

    Args:
        subject (str): 令牌主体，一般为用户 UUID，将作为后续请求的用户身份凭证。
        role (str): 用户角色，放入 payload 方便前端解析。
        settings (Settings): 全局配置，用于获取过期时间、密钥和签发者(iss)。
        token_version (int): Token 的版本号，用于支持主动失效 Token（如修改密码后）。

    Returns:
        str: 生成的 JWT 字符串。

    Raises:
        RuntimeError: 当 JWT_SECRET 未配置或过短时抛出。
    """
    if not settings.jwt_secret or len(settings.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 characters")

    # 获取当前的 UTC 时间，避免时区带来的歧义
    now = datetime.now(UTC)

    # 构建 JWT Payload 载荷信息
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,  # 签发时间 (Issued At)
        "exp": now
        + timedelta(minutes=settings.access_token_expire_minutes),  # 过期时间 (Expiration Time)
        "iss": settings.app_name,  # 签发者 (Issuer)
        "ver": token_version,  # 自定义字段：Token 版本号
    }

    # 采用配置的算法（通常是 HS256）对载荷进行签名
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict:
    """
    功能归属：
    用户认证 -> 令牌解析与校验。

    函数职责：
    解析 JWT 并验证其签名、有效期和发行者。如果校验失败抛出业务异常。

    调用方：
    `app.auth.dependencies.get_current_user` 鉴权中间件。

    Args:
        token (str): 客户端传来的 JWT 字符串。
        settings (Settings): 全局配置。

    Returns:
        dict: 解析成功后的 Payload 数据字典。

    Raises:
        AppError: 如果 Token 无效、过期或缺失必填字段，抛出 401 错误。
    """
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
