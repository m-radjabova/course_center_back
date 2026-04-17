from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_teacher_or_admin
from app.models.user import User
from app.schemas.attendance import AttendanceCreate, AttendanceResponse, AttendanceUpdate
from app.services.attendance_service import AttendanceService

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("/lessons/{lesson_id}", response_model=list[AttendanceResponse])
def list_attendance(lesson_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return AttendanceService(db).list_attendance(lesson_id, current_user)


@router.post("/", response_model=AttendanceResponse, status_code=status.HTTP_201_CREATED)
def mark_attendance(
    payload: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
):
    return AttendanceService(db).mark_attendance(payload, current_user)


@router.patch("/{attendance_id}", response_model=AttendanceResponse)
def update_attendance(
    attendance_id: str,
    payload: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
):
    return AttendanceService(db).update_attendance(attendance_id, payload, current_user)
