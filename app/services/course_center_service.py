from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course_center import CourseCenter
from app.schemas.course_centers import CourseCenterCreate, CourseCenterUpdate
from app.services.base import BaseService, parse_uuid


class CourseCenterService(BaseService):
    def list_course_centers(self) -> list[CourseCenter]:
        return list(
            self.db.execute(select(CourseCenter).order_by(CourseCenter.created_at.desc())).scalars().unique()
        )

    def get_course_center(self, course_center_id: str) -> CourseCenter:
        course_center = self.db.get(CourseCenter, parse_uuid(course_center_id, "course center id"))
        if not course_center:
            raise self.not_found("Course center")
        return course_center

    def create_course_center(self, payload: CourseCenterCreate) -> CourseCenter:
        course_center = CourseCenter(**payload.model_dump())
        self.db.add(course_center)
        self.commit()
        return self.refresh(course_center)

    def update_course_center(self, course_center_id: str, payload: CourseCenterUpdate) -> CourseCenter:
        course_center = self.get_course_center(course_center_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(course_center, field, value)
        self.db.add(course_center)
        self.commit()
        return self.refresh(course_center)


def get_course_center_service(db: Session) -> CourseCenterService:
    return CourseCenterService(db)
