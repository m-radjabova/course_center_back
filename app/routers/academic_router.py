from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_admin, require_teacher_or_admin
from app.models.user import User
from app.schemas.course import (
    AttendanceCreate,
    AttendanceOut,
    AttendanceUpdate,
    EnrollmentCreate,
    EnrollmentOut,
    EnrollmentUpdate,
    LessonCreate,
    LessonOut,
    LessonUpdate,
    MonthlyPaymentCreate,
    MonthlyPaymentOut,
    MonthlyPaymentUpdate,
    StudentMonthlyJournalOut,
)
from app.services import academic_service

router = APIRouter(prefix="/academic", tags=["Academic"])


@router.get("/groups/{group_id}/students", response_model=list[EnrollmentOut])
def list_group_students(
    group_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return academic_service.list_group_students(db, group_id)


@router.post("/groups/{group_id}/students", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
def enroll_student(
    group_id: str,
    payload: EnrollmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        enrollment = academic_service.enroll_student(db, group_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not enrollment:
        raise HTTPException(status_code=404, detail="Group not found")
    return enrollment


@router.patch("/enrollments/{enrollment_id}", response_model=EnrollmentOut)
def update_enrollment(
    enrollment_id: str,
    payload: EnrollmentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    enrollment = academic_service.update_enrollment(db, enrollment_id, payload)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return enrollment


@router.get("/lessons", response_model=list[LessonOut])
def list_lessons(
    group_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return academic_service.list_lessons(db, group_id)


@router.post("/lessons", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
def create_lesson(payload: LessonCreate, db: Session = Depends(get_db), _: User = Depends(require_teacher_or_admin)):
    try:
        return academic_service.create_lesson(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/lessons/{lesson_id}", response_model=LessonOut)
def update_lesson(
    lesson_id: str,
    payload: LessonUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher_or_admin),
):
    try:
        lesson = academic_service.update_lesson(db, lesson_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


@router.get("/lessons/{lesson_id}/attendance", response_model=list[AttendanceOut])
def list_attendance(
    lesson_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return academic_service.list_attendance(db, lesson_id)


@router.post("/lessons/{lesson_id}/attendance", response_model=AttendanceOut, status_code=status.HTTP_201_CREATED)
def add_attendance(
    lesson_id: str,
    payload: AttendanceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher_or_admin),
):
    try:
        return academic_service.add_attendance(db, lesson_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/attendance/{attendance_id}", response_model=AttendanceOut)
def update_attendance(
    attendance_id: str,
    payload: AttendanceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher_or_admin),
):
    attendance = academic_service.update_attendance(db, attendance_id, payload)
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance not found")
    return attendance


@router.get("/payments", response_model=list[MonthlyPaymentOut])
def list_monthly_payments(
    group_id: str | None = Query(default=None),
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return academic_service.list_monthly_payments(db, group_id, year, month)


@router.post("/groups/{group_id}/payments", response_model=MonthlyPaymentOut, status_code=status.HTTP_201_CREATED)
def create_monthly_payment(
    group_id: str,
    payload: MonthlyPaymentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        return academic_service.create_monthly_payment(db, group_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/payments/{payment_id}", response_model=MonthlyPaymentOut)
def update_monthly_payment(
    payment_id: str,
    payload: MonthlyPaymentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    payment = academic_service.update_monthly_payment(db, payment_id, payload)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.get("/groups/{group_id}/students/{student_id}/journal", response_model=StudentMonthlyJournalOut)
def get_student_monthly_journal(
    group_id: str,
    student_id: str,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    journal = academic_service.get_student_monthly_journal(db, group_id, student_id, year, month)
    if not journal:
        raise HTTPException(status_code=404, detail="Student enrollment not found")
    return journal
