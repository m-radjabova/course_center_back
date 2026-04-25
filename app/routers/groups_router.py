from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_admin
from app.models.user import User
from app.schemas.groups import GroupCreate, GroupResponse, GroupUpdate
from app.services.group_service import GroupService

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.get("/", response_model=list[GroupResponse])
def list_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return GroupService(db).list_groups(current_user)


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(payload: GroupCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return GroupService(db).create_group(payload, current_user)


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return GroupService(db).get_group(group_id, current_user)


@router.patch("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: str,
    payload: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return GroupService(db).update_group(group_id, payload, current_user)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    GroupService(db).delete_group(group_id, current_user)
