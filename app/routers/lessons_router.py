from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_teacher_or_admin
from app.models.user import User
from app.schemas.lessons import LessonCreate, LessonResponse, LessonUpdate
from app.services.lesson_service import LessonService

router = APIRouter(prefix="/lessons", tags=["Lessons"])


@router.get("/", response_model=list[LessonResponse])
def list_lessons(
    group_id: str | None = Query(default=None),
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return LessonService(db).list_lessons(current_user, group_id, year, month)


@router.post("/", response_model=LessonResponse, status_code=status.HTTP_201_CREATED)
def create_lesson(payload: LessonCreate, db: Session = Depends(get_db), current_user: User = Depends(require_teacher_or_admin)):
    return LessonService(db).create_lesson(payload, current_user)


@router.patch("/{lesson_id}", response_model=LessonResponse)
def update_lesson(
    lesson_id: str,
    payload: LessonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
):
    return LessonService(db).update_lesson(lesson_id, payload, current_user)
