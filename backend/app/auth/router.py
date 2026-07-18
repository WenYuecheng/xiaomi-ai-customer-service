"""
文件职责：
定义用户认证模块的 HTTP 路由接口（Controller 层），负责接收 HTTP 请求并编排业务服务。

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

    异常处理：
    鉴权失败将由 `authenticate` 抛出 401 错误，并被全局异常处理器捕获返回。
    """
    user = authenticate(session, form.username, form.password)
    token = create_access_token(
        user.id,
        user.role.value,
        request.app.state.settings,
        user.token_version,
    )
    return TokenResponse(access_token=token)


@router.post("/register", status_code=201)
def register(
    request: Request,
    payload: RegisterRequest,
    session: SessionDep,
) -> AuthSessionResponse:
    limiter: RegistrationRateLimiter = request.app.state.registration_rate_limiter
    limiter.check(request.client.host if request.client else "unknown")
    user = create_user(session, payload.username, payload.password, UserRole.user.value)
    session.add(
        BehaviorEvent(
            user_id=user.id,
            event_type="audit:auth:registered",
            payload={"action": "registered"},
        )
    )
    session.commit()
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
    """
    return UserResponse.model_validate(current_user)
