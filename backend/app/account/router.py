from fastapi import APIRouter, Response

from app.account.schemas import ChangePasswordRequest, ProfileUpdateRequest
from app.account.service import change_password, update_profile
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
