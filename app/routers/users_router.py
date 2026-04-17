from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import _resolve_user_from_token, get_current_user
from app.dependencies.roles import require_admin
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.users import ChangePasswordRequest, CurrentUserUpdate, UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    current_user: User | None = None

    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        current_user = _resolve_user_from_token(token, db)

    if current_user is None:
        if payload.roles != [UserRole.STUDENT]:
            raise HTTPException(status_code=403, detail="Public registration can only create student accounts")
        return UserService(db).create_user(payload)

    if not current_user.has_any_role(UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Permission denied")

    return UserService(db).create_user(payload)


@router.get("/", response_model=list[UserResponse])
def list_users(
    role: UserRole | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return UserService(db).list_users(role)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: CurrentUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService(db).update_current_user(current_user, payload)


@router.patch("/me/password", response_model=UserResponse)
def change_my_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService(db).change_password(current_user, payload.current_password, payload.new_password)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return UserService(db).get_user(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, payload: UserUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return UserService(db).update_user(user_id, payload)
