from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_current_user_optional
from app.dependencies.roles import require_admin
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import ChangePasswordSchema, ResetPasswordSchema, UserCreate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return user_service.update_current_user(db, current_user, payload)


@router.patch("/me/password", response_model=UserOut)
def change_my_password(
    payload: ChangePasswordSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return user_service.change_my_password(db, current_user, payload.current_password, payload.new_password)


@router.post("/me/avatar", response_model=UserOut)
def upload_my_avatar(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return user_service.update_user_avatar(db, current_user, image)


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_new_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    # current_user: User | None = Depends(get_current_user_optional),
):
    total_users = db.query(User).count()

    if total_users == 0:
        return user_service.create_user(db, payload)

    # if current_user is None:
    #     if payload.role != UserRole.USER:
    #         raise HTTPException(status_code=403, detail="Public registration can only create student accounts")
    #     return user_service.create_user(db, payload)

    # if current_user.role != UserRole.ADMIN:
    #     raise HTTPException(status_code=403, detail="Permission denied")

    return user_service.create_user(db, payload)


@router.get("/", response_model=list[UserOut])
def list_users(
    role: UserRole | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return user_service.get_users(db, role)


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.role != UserRole.ADMIN and current_user.id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, payload: UserUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user = user_service.update_user(db, user_id, payload)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}/password", response_model=UserOut)
def reset_user_password(
    user_id: str,
    payload: ResetPasswordSchema,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user_service.change_password(db, user, payload.new_password)


@router.post("/{user_id}/avatar", response_model=UserOut)
def upload_user_avatar(
    user_id: str,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = user_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user_service.update_user_avatar(db, user, image)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    user_service.delete_user(db, user_id)
