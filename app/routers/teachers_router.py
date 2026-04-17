from pydantic import BaseModel
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.roles import require_admin
from app.models.user import User
from app.schemas.profiles import TeacherDetailResponse, TeacherProfileCreate, TeacherProfileResponse, TeacherProfileUpdate
from app.schemas.users import UserCreate
from app.services.teacher_service import TeacherService
from app.services.user_service import UserService

router = APIRouter(prefix="/teachers", tags=["Teachers"])


class TeacherCreateRequest(BaseModel):
    user: UserCreate
    profile: TeacherProfileCreate


@router.get("/", response_model=list[TeacherDetailResponse])
def list_teachers(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return TeacherService(db).list_teachers()


@router.post("/", response_model=TeacherDetailResponse, status_code=status.HTTP_201_CREATED)
def create_teacher(payload: TeacherCreateRequest, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return TeacherService(db).create_teacher(payload.user, payload.profile)


@router.post("/{user_id}/profile", response_model=TeacherProfileResponse, status_code=status.HTTP_201_CREATED)
def create_teacher_profile(
    user_id: str,
    payload: TeacherProfileCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return UserService(db).create_teacher_profile(user_id, payload)


@router.patch("/{user_id}/profile", response_model=TeacherProfileResponse)
def update_teacher_profile(
    user_id: str,
    payload: TeacherProfileUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return UserService(db).update_teacher_profile(user_id, payload)
