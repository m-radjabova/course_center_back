from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    title: str = Field(..., max_length=150)
    description: Optional[str] = None
    order: int = Field(default=1, ge=1)
    due_at: Optional[datetime] = None
    max_score: Optional[int] = Field(None, ge=1, le=5)
    is_required: bool = True


class AssignmentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=150)
    description: Optional[str] = None
    order: Optional[int] = Field(None, ge=1)
    due_at: Optional[datetime] = None
    max_score: Optional[int] = Field(None, ge=1, le=5)
    is_required: Optional[bool] = None


class AssignmentOut(BaseModel):
    id: UUID
    lesson_id: UUID
    title: str
    description: Optional[str]
    order: int
    due_at: Optional[datetime]
    max_score: Optional[int]
    is_required: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SubmissionCreate(BaseModel):
    text_answer: Optional[str] = None
    file_url: Optional[str] = None


class SubmissionOut(BaseModel):
    id: UUID
    assignment_id: UUID
    user_id: UUID
    username: Optional[str] = None
    text_answer: Optional[str]
    file_url: Optional[str]
    status: str
    score: Optional[int]
    submitted_at: datetime
    graded_at: Optional[datetime]

    class Config:
        from_attributes = True


class GradeSubmission(BaseModel):
    score: int = Field(..., ge=1, le=5)
    status: str = "graded"
