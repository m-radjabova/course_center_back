from pydantic import Field

from app.schemas.common import ORMModel, TimestampedSchema


class CourseCenterBase(ORMModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=120)
    description: str | None = None
    is_active: bool = True


class CourseCenterCreate(CourseCenterBase):
    pass


class CourseCenterUpdate(ORMModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    is_active: bool | None = None


class CourseCenterResponse(TimestampedSchema, CourseCenterBase):
    pass
