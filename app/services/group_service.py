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
            raise self.not_found("Guruh")
        return group

    def list_groups(self, current_user: User) -> list[Group]:
        statement = (
            self._get_group_query()
            .order_by(Group.created_at.desc())
        )
        if not self.is_super_admin(current_user):
            statement = statement.where(Group.course_center_id == self.require_course_center_id(current_user))
        if self.is_teacher_limited(current_user):
            statement = statement.where(Group.teacher_id == current_user.id)
        return list(self.db.execute(statement).scalars().unique())

    def get_group(self, group_id: str, current_user: User) -> Group:
        group = self._get_group_record(group_id)
        self.ensure_same_course_center(current_user, group.course_center_id, "Guruh")
        if self.is_teacher_limited(current_user) and group.teacher_id != current_user.id:
            raise self.forbidden("Siz faqat o'zingizga biriktirilgan guruhlarni ko'ra olasiz")
        return group

    def create_group(self, payload: GroupCreate, current_user: User) -> Group:
        course_center_id = self.require_course_center_id(current_user)
        self._validate_group_refs(payload.course_id, payload.teacher_id, payload.room_id, current_user=current_user)
        group = Group(**payload.model_dump(), course_center_id=course_center_id)
        self.db.add(group)
        self.commit()
        return self._get_group_record(str(group.id))

    def update_group(self, group_id: str, payload: GroupUpdate, current_user: User) -> Group:
        group = self.get_group(group_id, current_user)
        data = payload.model_dump(exclude_unset=True)
        self._validate_group_refs(
            data.get("course_id"),
            data.get("teacher_id"),
            data.get("room_id"),
            partial=True,
            current_user=current_user,
        )
        for field, value in data.items():
            setattr(group, field, value)
        self.db.add(group)
        self.commit()
        return self._get_group_record(str(group.id))

    def delete_group(self, group_id: str, current_user: User) -> None:
        group = self.get_group(group_id, current_user)
        self.db.delete(group)
        self.commit()

    def _validate_group_refs(self, course_id, teacher_id, room_id, current_user: User, partial: bool = False) -> None:
        if course_id is not None:
            course = self.db.get(Course, parse_uuid(course_id, "course id"))
            if not course:
                raise self.bad_request("Kurs topilmadi")
            self.ensure_same_course_center(current_user, course.course_center_id, "Kurs")
        elif not partial:
            raise self.bad_request("Kurs tanlanishi shart")

        if teacher_id is not None:
            teacher = self.db.get(User, parse_uuid(teacher_id, "teacher id"))
            if not teacher or UserRole.TEACHER not in teacher.roles:
                raise self.bad_request("O'qituvchi topilmadi")
            self.ensure_same_course_center(current_user, teacher.course_center_id, "O'qituvchi")

        if room_id is not None:
            room = self.db.get(Room, parse_uuid(room_id, "room id"))
            if not room:
                raise self.bad_request("Xona topilmadi")
            self.ensure_same_course_center(current_user, room.course_center_id, "Xona")


def get_group_service(db: Session) -> GroupService:
    return GroupService(db)
