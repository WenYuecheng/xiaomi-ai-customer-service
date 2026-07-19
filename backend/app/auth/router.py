"""
文件职责：
该文件负责定义用户认证模块的 HTTP 路由接口（Controller 层），接收 HTTP 请求并编排业务服务。

所属功能：
用户认证 -> 路由层。

外部入口：
- POST `/api/v1/auth/login`
- GET `/api/v1/auth/me`
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.dependencies import CurrentUserDep
from app.auth.rate_limit import RegistrationRateLimiter
from app.auth.schemas import (
    AuthSessionResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.auth.security import create_access_token
from app.auth.service import authenticate, create_user
from app.db.base import SessionDep
from app.db.models import BehaviorEvent, UserRole

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login")
def login(
    request: Request,
    session: SessionDep,
    # 接收 `application/x-www-form-urlencoded` 格式的用户名密码，遵循 OAuth2 规范
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    """
    功能：用户登录

    外部入口：
    POST /api/v1/auth/login

    执行链：
    login (Controller)
    → OAuth2PasswordRequestForm (参数提取)
    → authenticate (服务层鉴权，数据库查询 + 密码校验)
    → create_access_token (签发 JWT)
    → TokenResponse (组装响应)

    Args:
        request (Request): FastAPI 的请求对象。
        session (SessionDep): 数据库会话依赖。
        form (OAuth2PasswordRequestForm): 表单数据，包含 username 和 password。

    Returns:
        TokenResponse: 包含生成的 access_token 的响应对象。

    Raises:
        AppError: 鉴权失败时由 authenticate 抛出 401 错误。
    """
    # 步骤 1：调用业务服务层进行身份验证
    user = authenticate(session, form.username, form.password)

    # 步骤 2：认证成功后，为该用户签发 JWT 令牌
    token = create_access_token(
        user.id,
        user.role.value,
        request.app.state.settings,
        user.token_version,
    )

    # 步骤 3：返回标准的 OAuth2 响应结构
    return TokenResponse(access_token=token)


@router.post("/register", status_code=201)
def register(
    request: Request,
    payload: RegisterRequest,
    session: SessionDep,
) -> AuthSessionResponse:
    """
    功能：用户注册

    外部入口：
    POST /api/v1/auth/register

    Args:
        request (Request): FastAPI 请求对象，用于获取全局限流器和客户端信息。
        payload (RegisterRequest): 客户端传入的注册数据验证模型。
        session (SessionDep): 数据库会话依赖。

    Returns:
        AuthSessionResponse: 包含新用户的 Token 和详细信息的响应体。

    Raises:
        AppError: 如果用户已存在或达到频率限制时抛出。
    """
    # 步骤 1：获取全局注册频率限制器，并检查当前客户端 IP 是否触发限流
    limiter: RegistrationRateLimiter = request.app.state.registration_rate_limiter
    limiter.check(request.client.host if request.client else "unknown")

    # 步骤 2：调用服务层逻辑在数据库中创建用户记录
    user = create_user(session, payload.username, payload.password, UserRole.user.value)

    # 步骤 3：记录用户注册的审计事件（行为日志）
    session.add(
        BehaviorEvent(
            user_id=user.id,
            event_type="audit:auth:registered",
            payload={"action": "registered"},
        )
    )
    session.commit()

    # 步骤 4：自动为刚注册的用户签发登录令牌，免去其再次登录的步骤
    token = create_access_token(
        user.id,
        user.role.value,
        request.app.state.settings,
        user.token_version,
    )
    return AuthSessionResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me")
def me(current_user: CurrentUserDep) -> UserResponse:
    """
    功能：获取当前登录用户信息

    外部入口：
    GET /api/v1/auth/me

    流程位置：
    利用 `CurrentUserDep` 依赖自动完成 Token 提取、验证和数据库查询。如果到达函数体，说明用户合法。

    Args:
        current_user (CurrentUserDep): 经由依赖注入获取的已通过认证的当前用户。

    Returns:
        UserResponse: 当前用户的脱敏信息对象。
    """
    # 利用 Pydantic 模型的 model_validate 方法将 ORM 对象转为响应字典，自动过滤掉密码等敏感字段
    return UserResponse.model_validate(current_user)
