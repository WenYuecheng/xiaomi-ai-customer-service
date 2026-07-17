from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.dependencies import CurrentUserDep
from app.auth.schemas import TokenResponse, UserResponse
from app.auth.security import create_access_token
from app.auth.service import authenticate
from app.db.base import SessionDep

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login")
def login(
    request: Request,
    session: SessionDep,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    user = authenticate(session, form.username, form.password)
    token = create_access_token(user.id, user.role.value, request.app.state.settings)
    return TokenResponse(access_token=token)


@router.get("/me")
def me(current_user: CurrentUserDep) -> UserResponse:
    return UserResponse.model_validate(current_user)

