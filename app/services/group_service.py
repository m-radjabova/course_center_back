from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.course import Course
from app.models.enums import UserRole
from app.models.group import Group
from app.models.room import Room
from app.models.user import User
from app.schemas.groups import GroupCreate, GroupUpdate
from app.services.base import BaseService, parse_uuid


class GroupService(BaseService):
    def _get_group_query(self):
        return select(Group).options(joinedload(Group.course), joinedload(Group.teacher), joinedload(Group.room))

    def _get_group_record(self, group_id: str) -> Group:
        group = self.db.execute(
            self._get_group_query().where(Group.id == parse_uuid(group_id, "group id"))
        ).scalar_one_or_none()
        if not group:
            raise self.not_found("Group")
        return group

    def list_groups(self, current_user: User) -> list[Group]:
        statement = (
            self._get_group_query()
            .order_by(Group.created_at.desc())
        )
        if current_user.has_role(UserRole.TEACHER) and not current_user.has_role(UserRole.ADMIN):
            statement = statement.where(Group.teacher_id == current_user.id)
        return list(self.db.execute(statement).scalars().unique())

    def get_group(self, group_id: str, current_user: User) -> Group:
        group = self._get_group_record(group_id)
        if current_user.has_role(UserRole.TEACHER) and not current_user.has_role(UserRole.ADMIN) and group.teacher_id != current_user.id:
            raise self.forbidden("You can only access your assigned groups")
        return group

    def create_group(self, payload: GroupCreate) -> Group:
        self._validate_group_refs(payload.course_id, payload.teacher_id, payload.room_id)
        group = Group(**payload.model_dump())
        self.db.add(group)
        self.commit()
        return self._get_group_record(str(group.id))

    def update_group(self, group_id: str, payload: GroupUpdate) -> Group:
        group = self._get_group_record(group_id)
        data = payload.model_dump(exclude_unset=True)
        self._validate_group_refs(data.get("course_id"), data.get("teacher_id"), data.get("room_id"), partial=True)
        for field, value in data.items():
            setattr(group, field, value)
        self.db.add(group)
        self.commit()
        return self._get_group_record(str(group.id))

    def delete_group(self, group_id: str) -> None:
        group = self._get_group_record(group_id)
        self.db.delete(group)
        self.commit()

    def _validate_group_refs(self, course_id, teacher_id, room_id, partial: bool = False) -> None:
        if course_id is not None:
            course = self.db.get(Course, parse_uuid(course_id, "course id"))
            if not course:
                raise self.bad_request("Course not found")
        elif not partial:
            raise self.bad_request("Course is required")

        if teacher_id is not None:
            teacher = self.db.get(User, parse_uuid(teacher_id, "teacher id"))
            if not teacher or UserRole.TEACHER not in teacher.roles:
                raise self.bad_request("Teacher not found")

        if room_id is not None:
            room = self.db.get(Room, parse_uuid(room_id, "room id"))
            if not room:
                raise self.bad_request("Room not found")


def get_group_service(db: Session) -> GroupService:
    return GroupService(db)
