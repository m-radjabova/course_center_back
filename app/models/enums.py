from enum import Enum

from sqlalchemy import Enum as SAEnum


def enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


def sql_enum(enum_cls: type[Enum], name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=enum_values,
        native_enum=True,
        validate_strings=True,
    )


class UserRole(str, Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class GroupStatus(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    FINISHED = "finished"
    ARCHIVED = "archived"


class EnrollmentStatus(str, Enum):
    ACTIVE = "active"
    LEFT = "left"
    FINISHED = "finished"


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"


class PaymentMethod(str, Enum):
    CASH = "cash"
    CARD = "card"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
