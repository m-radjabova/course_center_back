from sqlalchemy.orm import Session, joinedload

from app.models.course import Course, CourseGroup
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.course import CourseCreate, CourseGroupCreate, CourseGroupUpdate, CourseUpdate
from app.services.utils import parse_uuid


def _course_query(db: Session):
    return db.query(Course)


def _group_query(db: Session):
    return db.query(CourseGroup).options(
        joinedload(CourseGroup.course),
        joinedload(CourseGroup.teacher),
    )


def list_courses(db: Session):
    return _course_query(db).order_by(Course.created_at.desc()).all()


def create_course(db: Session, payload: CourseCreate):
    course = Course(**payload.model_dump())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def get_course(db: Session, course_id: str):
    return _course_query(db).filter(Course.id == parse_uuid(course_id, "course id")).first()


def update_course(db: Session, course_id: str, payload: CourseUpdate):
    course = get_course(db, course_id)
    if not course:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def delete_course(db: Session, course_id: str):
    course = get_course(db, course_id)
    if not course:
        return False
    db.delete(course)
    db.commit()
    return True


def list_groups(db: Session):
    return _group_query(db).order_by(CourseGroup.created_at.desc()).all()


def create_group(db: Session, payload: CourseGroupCreate):
    teacher_id = parse_uuid(payload.teacher_id, "teacher id") if payload.teacher_id else None
    if teacher_id:
        teacher = db.query(User).filter(User.id == teacher_id, User.role == UserRole.TEACHER).first()
        if not teacher:
            raise ValueError("Teacher not found")
    group = CourseGroup(
        course_id=parse_uuid(payload.course_id, "course id"),
        teacher_id=teacher_id,
        name=payload.name,
        room=payload.room,
        capacity=payload.capacity,
        schedule_summary=payload.schedule_summary,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return get_group(db, str(group.id))


def get_group(db: Session, group_id: str):
    return _group_query(db).filter(CourseGroup.id == parse_uuid(group_id, "group id")).first()


def update_group(db: Session, group_id: str, payload: CourseGroupUpdate):
    group = get_group(db, group_id)
    if not group:
        return None
    data = payload.model_dump(exclude_unset=True)
    if "course_id" in data and data["course_id"]:
        group.course_id = parse_uuid(data["course_id"], "course id")
    if "teacher_id" in data:
        group.teacher_id = parse_uuid(data["teacher_id"], "teacher id") if data["teacher_id"] else None
        if group.teacher_id:
            teacher = db.query(User).filter(User.id == group.teacher_id, User.role == UserRole.TEACHER).first()
            if not teacher:
                raise ValueError("Teacher not found")
    for field in ("name", "room", "capacity", "schedule_summary", "start_date", "end_date", "status"):
        if field in data:
            setattr(group, field, data[field])
    db.add(group)
    db.commit()
    db.refresh(group)
    return get_group(db, str(group.id))


def delete_group(db: Session, group_id: str):
    group = get_group(db, group_id)
    if not group:
        return False
    db.delete(group)
    db.commit()
    return True
