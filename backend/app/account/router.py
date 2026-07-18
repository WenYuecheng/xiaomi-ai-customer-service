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
    return UserResponse.model_validate(update_profile(session, current_user, payload))


@router.post("/change-password", status_code=204)
def post_change_password(
    payload: ChangePasswordRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    change_password(session, current_user, payload)
    return Response(status_code=204)


@router.get("/dashboard")
def get_dashboard(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> AccountDashboardResponse:
    return account_dashboard(session, current_user)


@router.get("/activities")
def get_activities(
    session: SessionDep,
    current_user: CurrentUserDep,
    cursor: Annotated[str | None, Query(max_length=500)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ActivityListResponse:
    return paginate_activities(collect_activities(session, current_user.id), cursor, limit)
