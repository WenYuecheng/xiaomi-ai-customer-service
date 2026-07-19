"""
文件职责：
该文件负责定义账号相关的 API 路由。

所属功能：
账号模块（Account Module），处理更新个人资料、修改密码、获取仪表盘数据和
用户活动列表等 HTTP 请求。

主要流程：
1. 接收客户端的 HTTP 请求。
2. 验证用户凭证（通过 CurrentUserDep）。
3. 提取并校验请求载荷（Payload）和查询参数。
4. 调用 service 层相关的业务逻辑函数进行处理。
5. 将 service 层的结果格式化为响应模型（Response）并返回。
"""

from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.account.schemas import (
    AccountDashboardResponse,
    ActivityListResponse,
    ChangePasswordRequest,
    ProfileUpdateRequest,
)
from app.account.service import (
    account_dashboard,
    change_password,
    collect_activities,
    paginate_activities,
    update_profile,
)
from app.auth.dependencies import CurrentUserDep
from app.auth.schemas import UserResponse
from app.db.base import SessionDep

router = APIRouter(prefix="/account", tags=["account"])


@router.patch("/profile")
def patch_profile(
    payload: ProfileUpdateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> UserResponse:
    """
    修改当前用户的个人资料。

    Args:
        payload (ProfileUpdateRequest): 包含需更新资料的请求体。
        session (SessionDep): 数据库会话依赖。
        current_user (CurrentUserDep): 当前登录的已认证用户。

    Returns:
        UserResponse: 包含更新后用户信息的响应对象。

    Raises:
        无特定异常。
    """
    # 调用 service 层的更新配置逻辑，并将返回的 User 模型验证后转换为 UserResponse
    return UserResponse.model_validate(update_profile(session, current_user, payload))


@router.post("/change-password", status_code=204)
def post_change_password(
    payload: ChangePasswordRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    """
    修改当前用户的登录密码。

    Args:
        payload (ChangePasswordRequest): 包含当前密码及新密码的请求体。
        session (SessionDep): 数据库会话依赖。
        current_user (CurrentUserDep): 当前登录的已认证用户。

    Returns:
        Response: 返回状态码为 204 的空响应，表示密码修改成功。

    Raises:
        AppError: 如果当前密码错误，服务层会抛出此异常。
    """
    # 委派给 service 层的 change_password 执行密码校验及修改操作
    change_password(session, current_user, payload)
    return Response(status_code=204)


@router.get("/dashboard")
def get_dashboard(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AccountDashboardResponse:
    """
    获取当前用户的个人仪表盘数据。

    Args:
        session (SessionDep): 数据库会话依赖。
        current_user (CurrentUserDep): 当前登录的已认证用户。

    Returns:
        AccountDashboardResponse: 包含各项统计、近期活动和偏好数据的仪表盘响应。

    Raises:
        无特定异常。
    """
    return account_dashboard(session, current_user)


@router.get("/activities")
def get_activities(
    session: SessionDep,
    current_user: CurrentUserDep,
    cursor: Annotated[str | None, Query(max_length=500)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ActivityListResponse:
    """
    分页获取当前用户的近期活动列表。

    Args:
        session (SessionDep): 数据库会话依赖。
        current_user (CurrentUserDep): 当前登录的已认证用户。
        cursor (str | None): 分页游标，通过 base64 编码，限制最大长度。
        limit (int): 本次请求返回的最大记录数，介于 1 到 50 之间，默认 20。

    Returns:
        ActivityListResponse: 包含活动列表和下一页游标的响应。

    Raises:
        AppError: 若游标无效，在服务层解析时可能会抛出异常。
    """
    # 首先全量收集用户所有活动，然后根据 cursor 和 limit 进行分页切片返回
    return paginate_activities(collect_activities(session, current_user.id), cursor, limit)
