from pydantic import BaseModel
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_admin, require_teacher_or_admin
from app.models.user import User
from app.schemas.enrollments import BulkEnrollmentCreate, EnrollmentCreate, EnrollmentResponse, EnrollmentUpdate
from app.schemas.profiles import StudentDetailResponse, StudentProfileCreate, StudentProfileResponse, StudentProfileUpdate
from app.schemas.users import UserCreate
from app.services.student_service import StudentService
from app.services.user_service import UserService

router = APIRouter(prefix="/students", tags=["Students"])


class StudentCreateRequest(BaseModel):
    user: UserCreate
    profile: StudentProfileCreate


@router.get("/", response_model=list[StudentDetailResponse])
def list_students(
    unassigned_only: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher_or_admin),
):
    service = StudentService(db)
    if unassigned_only:
        return service.list_unassigned_students()
    return service.list_students()


@router.post("/", response_model=StudentDetailResponse, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreateRequest, db: Session = Depends(get_db), _: User = Depends(require_teacher_or_admin)):
    return StudentService(db).create_student(payload.user, payload.profile)


@router.post("/{user_id}/profile", response_model=StudentProfileResponse, status_code=status.HTTP_201_CREATED)
def create_student_profile(
    user_id: str,
    payload: StudentProfileCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher_or_admin),
):
    return UserService(db).create_student_profile(user_id, payload)


@router.patch("/{user_id}/profile", response_model=StudentProfileResponse)
def update_student_profile(
    user_id: str,
    payload: StudentProfileUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher_or_admin),
):
    return UserService(db).update_student_profile(user_id, payload)


@router.get("/groups/{group_id}/enrollments", response_model=list[EnrollmentResponse])
def list_group_enrollments(group_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return StudentService(db).list_group_enrollments(group_id, current_user)


@router.post("/enrollments", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
def enroll_student(payload: EnrollmentCreate, db: Session = Depends(get_db), _: User = Depends(require_teacher_or_admin)):
    return StudentService(db).enroll_student(payload)


@router.post("/enrollments/bulk", response_model=list[EnrollmentResponse], status_code=status.HTTP_201_CREATED)
def bulk_enroll_students(
    payload: BulkEnrollmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher_or_admin),
):
    return StudentService(db).bulk_enroll_students(payload)


@router.patch("/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
def update_enrollment(
    enrollment_id: str,
    payload: EnrollmentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher_or_admin),
):
    return StudentService(db).update_enrollment(enrollment_id, payload)
