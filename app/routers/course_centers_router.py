from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_super_admin
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.course_centers import CourseCenterCreate, CourseCenterResponse, CourseCenterUpdate
from app.services.course_center_service import CourseCenterService

router = APIRouter(prefix="/course-centers", tags=["Course Centers"])


@router.get("/", response_model=list[CourseCenterResponse])
def list_course_centers(
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    return CourseCenterService(db).list_course_centers()


@router.post("/", response_model=CourseCenterResponse, status_code=status.HTTP_201_CREATED)
def create_course_center(
    payload: CourseCenterCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    return CourseCenterService(db).create_course_center(payload)


@router.get("/{course_center_id}", response_model=CourseCenterResponse)
def get_course_center(
    course_center_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course_center = CourseCenterService(db).get_course_center(course_center_id)
    if not current_user.has_role(UserRole.SUPER_ADMIN) and str(course_center.id) != str(current_user.course_center_id):
        raise CourseCenterService(db).forbidden("Course center boshqa foydalanuvchiga tegishli")
    return course_center


@router.patch("/{course_center_id}", response_model=CourseCenterResponse)
def update_course_center(
    course_center_id: str,
    payload: CourseCenterUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    return CourseCenterService(db).update_course_center(course_center_id, payload)
