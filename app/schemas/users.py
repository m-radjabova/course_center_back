from pydantic import Field, field_validator

from app.schemas.common import ORMModel, TimestampedSchema, validate_app_email
from app.schemas.enums import UserRole, UserStatus


class UserBase(ORMModel):
    full_name: str = Field(min_length=3, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: str
    roles: list[UserRole] = Field(min_length=1)
    status: UserStatus = UserStatus.ACTIVE

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return validate_app_email(value)

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, value: list[UserRole]) -> list[UserRole]:
        unique_roles = list(dict.fromkeys(value))
        if not unique_roles:
            raise ValueError("At least one role is required")
        return unique_roles


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)


class UserUpdate(ORMModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    roles: list[UserRole] | None = Field(default=None, min_length=1)
    status: UserStatus | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_app_email(value)

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, value: list[UserRole] | None) -> list[UserRole] | None:
        if value is None:
            return value
        unique_roles = list(dict.fromkeys(value))
        if not unique_roles:
            raise ValueError("At least one role is required")
        return unique_roles


class CurrentUserUpdate(ORMModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_app_email(value)


class ChangePasswordRequest(ORMModel):
    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class UserResponse(TimestampedSchema):
    full_name: str
    email: str
    phone: str | None = None
    roles: list[UserRole]
    status: UserStatus

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return validate_app_email(value)
