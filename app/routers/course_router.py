from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.roles import require_admin, require_teacher_or_admin
from app.models.user import User
from app.schemas.course import CourseCreate, CourseGroupCreate, CourseGroupOut, CourseGroupUpdate, CourseOut, CourseUpdate
from app.services import course_service

router = APIRouter(prefix="/courses", tags=["Courses"])
groups_router = APIRouter(prefix="/groups", tags=["Groups"])


@router.get("/", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return course_service.list_courses(db)


@router.post("/", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return course_service.create_course(db, payload)


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    course = course_service.get_course(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.patch("/{course_id}", response_model=CourseOut)
def update_course(course_id: str, payload: CourseUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    course = course_service.update_course(db, course_id, payload)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(course_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if not course_service.delete_course(db, course_id):
        raise HTTPException(status_code=404, detail="Course not found")


@groups_router.get("/", response_model=list[CourseGroupOut])
def list_groups(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return course_service.list_groups(db)


@groups_router.post("/", response_model=CourseGroupOut, status_code=status.HTTP_201_CREATED)
def create_group(payload: CourseGroupCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    try:
        return course_service.create_group(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@groups_router.get("/{group_id}", response_model=CourseGroupOut)
def get_group(group_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    group = course_service.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    if user.role.value == "teacher" and group.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="Permission denied")
    return group


@groups_router.patch("/{group_id}", response_model=CourseGroupOut)
def update_group(
    group_id: str,
    payload: CourseGroupUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_teacher_or_admin),
):
    try:
        group = course_service.update_group(db, group_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@groups_router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: str, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if not course_service.delete_group(db, group_id):
        raise HTTPException(status_code=404, detail="Group not found")
