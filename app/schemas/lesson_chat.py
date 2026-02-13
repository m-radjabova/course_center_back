from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LessonChatMessageCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=3000)


class LessonChatMessageUpdate(BaseModel):
    text: str = Field(..., min_length=1, max_length=3000)


class LessonChatMessageOut(BaseModel):
    id: UUID
    thread_id: UUID
    sender_id: UUID
    sender_username: str | None = None
    text: str
    created_at: datetime

    class Config:
        from_attributes = True


class LessonChatThreadOut(BaseModel):
    id: UUID
    lesson_id: UUID
    student_id: UUID
    student_username: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True
