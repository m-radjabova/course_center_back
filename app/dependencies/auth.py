from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.jwt import decode_token
from app.models.user import User

bearer_scheme = HTTPBearer()
optional_bearer_scheme = HTTPBearer(auto_error=False)


def _resolve_user_from_token(token: str | None, db: Session):
    if not token:
        return None

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        user_uuid = UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid user id in token") from exc

    user = db.get(User, user_uuid)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    return _resolve_user_from_token(creds.credentials, db)


def get_current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(optional_bearer_scheme),
    db: Session = Depends(get_db),
):
    if creds is None:
        return None
    return _resolve_user_from_token(creds.credentials, db)
