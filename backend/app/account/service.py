from sqlalchemy.orm import Session

from app.account.schemas import ChangePasswordRequest, ProfileUpdateRequest
from app.auth.security import hash_password, verify_password
from app.core.errors import AppError
from app.db.models import BehaviorEvent, User


def update_profile(session: Session, user: User, payload: ProfileUpdateRequest) -> User:
    changed_fields: list[str] = []
    if payload.display_name is not None and payload.display_name != user.display_name:
        user.display_name = payload.display_name
        changed_fields.append("display_name")
    if payload.avatar_key is not None and payload.avatar_key != user.avatar_key:
        user.avatar_key = payload.avatar_key
        changed_fields.append("avatar_key")
    if changed_fields:
        session.add(
            BehaviorEvent(
                user_id=user.id,
                event_type="audit:account:profile_updated",
                payload={"changed_fields": changed_fields},
            )
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def change_password(session: Session, user: User, payload: ChangePasswordRequest) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise AppError(400, "invalid_current_password", "当前密码不正确")
    user.password_hash = hash_password(payload.new_password)
    user.token_version += 1
    session.add(user)
    session.add(
        BehaviorEvent(
            user_id=user.id,
            event_type="audit:account:password_changed",
            payload={"action": "password_changed"},
        )
    )
    session.commit()
