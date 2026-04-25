from pydantic import BaseModel
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_admin, require_teacher_or_admin
from app.models.user import User
from app.schemas.enrollments import BulkEnrollmentCreate, EnrollmentCreate, EnrollmentResponse, EnrollmentUpdate
from app.schemas.profiles import (
    StudentDetailResponse,
    StudentListResponse,
    StudentProfileCreate,
    StudentProfileResponse,
    StudentProfileUpdate,
)
from app.schemas.users import UserCreate
from app.services.student_service import StudentService
from app.services.user_service import UserService

router = APIRouter(prefix="/students", tags=["Students"])


class StudentCreateRequest(BaseModel):
    user: UserCreate
    profile: StudentProfileCreate


@router.get("/", response_model=StudentListResponse)
def list_students(
    unassigned_only: bool = False,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=10_000),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
):
    service = StudentService(db)
    return service.list_students_paginated(
        current_user=current_user,
        page=page,
        limit=limit,
        search=search,
        unassigned_only=unassigned_only,
    )


@router.get("/{user_id}", response_model=StudentDetailResponse)
def get_student(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
):
    return StudentService(db).get_student(user_id, current_user)


@router.post("/", response_model=StudentDetailResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
):
    return StudentService(db).create_student(payload.user, payload.profile, current_user)


@router.post("/{user_id}/profile", response_model=StudentProfileResponse, status_code=status.HTTP_201_CREATED)
def create_student_profile(
    user_id: str,
    payload: StudentProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
):
    return UserService(db).create_student_profile(user_id, payload, current_user)


@router.patch("/{user_id}/profile", response_model=StudentProfileResponse)
def update_student_profile(
    user_id: str,
    payload: StudentProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
):
    return UserService(db).update_student_profile(user_id, payload, current_user)


@router.get("/groups/{group_id}/enrollments", response_model=list[EnrollmentResponse])
def list_group_enrollments(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return StudentService(db).list_group_enrollments(group_id, current_user)


@router.post("/enrollments", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
def enroll_student(
    payload: EnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
):
    return StudentService(db).enroll_student(payload, current_user)


@router.post("/enrollments/bulk", response_model=list[EnrollmentResponse], status_code=status.HTTP_201_CREATED)
def bulk_enroll_students(
    payload: BulkEnrollmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
):
    return StudentService(db).bulk_enroll_students(payload, current_user)


@router.patch("/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
def update_enrollment(
    enrollment_id: str,
    payload: EnrollmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_or_admin),
):
    return StudentService(db).update_enrollment(enrollment_id, payload, current_user)
