from datetime import date

from pydantic import Field, field_validator

from app.models.enums import UserRole, UserStatus
from app.schemas.common import ORMModel, TimestampedSchema, validate_app_email


class UserBase(ORMModel):
    full_name: str = Field(min_length=3, max_length=120)
    email: str
    phone: str | None = Field(default=None, max_length=30)
    phone_number: str | None = Field(default=None, max_length=30)
    notes: str | None = None
    specialization: str | None = Field(default=None, max_length=120)
    bio: str | None = None
    hired_at: date | None = None
    avatar: str | None = None
    role: UserRole
    status: UserStatus = UserStatus.ACTIVE

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return validate_app_email(value)


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserUpdate(ORMModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=120)
    email: str | None = None
    phone: str | None = Field(default=None, max_length=30)
    phone_number: str | None = Field(default=None, max_length=30)
    notes: str | None = None
    specialization: str | None = Field(default=None, max_length=120)
    bio: str | None = None
    hired_at: date | None = None
    avatar: str | None = None
    role: UserRole | None = None
    status: UserStatus | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_app_email(value)


class ChangePasswordSchema(ORMModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=128)


class ResetPasswordSchema(ORMModel):
    new_password: str = Field(min_length=6, max_length=128)


class UserOut(TimestampedSchema, UserBase):
    is_superuser: bool
