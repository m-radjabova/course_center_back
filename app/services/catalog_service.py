from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.course import Course, CourseFeeHistory
from app.models.room import Room
from app.schemas.courses import CourseCreate, CourseUpdate
from app.schemas.rooms import RoomCreate, RoomUpdate
from app.services.base import BaseService, parse_uuid


def _month_start(value: date | None = None) -> date:
    target = value or date.today()
    return date(target.year, target.month, 1)


def _next_month_start(value: date | None = None) -> date:
    target = _month_start(value)
    if target.month == 12:
        return date(target.year + 1, 1, 1)
    return date(target.year, target.month + 1, 1)


class CourseService(BaseService):
    def list_courses(self) -> list[Course]:
        statement = select(Course).options(selectinload(Course.fee_histories)).order_by(Course.name.asc())
        return list(self.db.execute(statement).scalars().unique())

    def get_course(self, course_id: str) -> Course:
        statement = (
            select(Course)
            .options(selectinload(Course.fee_histories))
            .where(Course.id == parse_uuid(course_id, "course id"))
        )
        course = self.db.execute(statement).scalar_one_or_none()
        if not course:
            raise self.not_found("Course")
        return course

    def create_course(self, payload: CourseCreate) -> Course:
        data = payload.model_dump()
        fee_effective_from = _month_start(data.pop("fee_effective_from", None))

        course = Course(**data)
        self.db.add(course)
        self.commit()
        self.refresh(course)

        history = CourseFeeHistory(
            course_id=course.id,
            amount=course.default_monthly_fee,
            effective_from=fee_effective_from,
        )
        self.db.add(history)
        self.commit()
        return self.get_course(str(course.id))

    def update_course(self, course_id: str, payload: CourseUpdate) -> Course:
        course = self.get_course(course_id)
        data = payload.model_dump(exclude_unset=True)
        fee_effective_from = data.pop("fee_effective_from", None)
        new_fee = data.pop("default_monthly_fee", None)

        for field, value in data.items():
            setattr(course, field, value)

        if new_fee is not None:
            if new_fee != course.default_monthly_fee:
                effective_from = _month_start(fee_effective_from) if fee_effective_from else _next_month_start()
                existing_history = next(
                    (item for item in course.fee_histories if item.effective_from == effective_from),
                    None,
                )
                if existing_history:
                    existing_history.amount = new_fee
                    self.db.add(existing_history)
                else:
                    self.db.add(
                        CourseFeeHistory(
                            course_id=course.id,
                            amount=new_fee,
                            effective_from=effective_from,
                        )
                    )
            course.default_monthly_fee = new_fee

        self.db.add(course)
        self.commit()
        return self.get_course(course_id)

    def delete_course(self, course_id: str) -> None:
        course = self.get_course(course_id)
        self.db.delete(course)
        self.commit()


class RoomService(BaseService):
    def list_rooms(self) -> list[Room]:
        return list(self.db.execute(select(Room).order_by(Room.name.asc())).scalars())

    def get_room(self, room_id: str) -> Room:
        room = self.db.get(Room, parse_uuid(room_id, "room id"))
        if not room:
            raise self.not_found("Room")
        return room

    def create_room(self, payload: RoomCreate) -> Room:
        room = Room(**payload.model_dump())
        self.db.add(room)
        self.commit()
        return self.refresh(room)

    def update_room(self, room_id: str, payload: RoomUpdate) -> Room:
        room = self.get_room(room_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(room, field, value)
        self.db.add(room)
        self.commit()
        return self.refresh(room)

    def delete_room(self, room_id: str) -> None:
        room = self.get_room(room_id)
        self.db.delete(room)
        self.commit()


def get_course_service(db: Session) -> CourseService:
    return CourseService(db)


def get_room_service(db: Session) -> RoomService:
    return RoomService(db)
