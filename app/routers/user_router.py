from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_admin
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create(user: UserCreate, db: Session = Depends(get_db)):
    return user_service.create_user(db, user)

@router.get("/", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    return user_service.get_users(db)

@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    # admin: User = Depends(require_admin) 
):
    db_user = user_service.get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.put("/{user_id}", response_model=UserOut)
def update_user_info(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    # admin: User = Depends(require_admin)
):
    updated_user = user_service.update_user(db, user_id, user_data)
    return updated_user


@router.put("/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: int,
    data: UserUpdate,  
    db: Session = Depends(get_db),
    # admin: User = Depends(require_admin),
):
    if not data.role:
        raise HTTPException(status_code=400, detail="role is required")
    return user_service.update_user(db, user_id, data)

@router.delete("/{user_id}", status_code=204)
def delete(
    user_id: int,
    db: Session = Depends(get_db),
    # admin: User = Depends(require_admin)
):
    user_service.delete_user(db, user_id)
