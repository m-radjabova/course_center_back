from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_admin
from app.models.user import User
from app.schemas.courses import CourseCreate, CourseResponse, CourseUpdate
from app.services.catalog_service import CourseService

router = APIRouter(prefix="/courses", tags=["Courses"])


@router.get("/", response_model=list[CourseResponse])
def list_courses(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return CourseService(db).list_courses(current_user)


@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return CourseService(db).create_course(payload, current_user)


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return CourseService(db).get_course(course_id, current_user)


@router.patch("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: str,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return CourseService(db).update_course(course_id, payload, current_user)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    CourseService(db).delete_course(course_id, current_user)
