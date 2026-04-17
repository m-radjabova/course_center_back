from datetime import datetime
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from email_validator import EmailNotValidError, validate_email


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedSchema(ORMModel):
    id: UUID
    created_at: datetime
    updated_at: datetime


LOCAL_EMAIL_PATTERN = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.local$", re.IGNORECASE)


def validate_app_email(value: str) -> str:
    normalized = value.strip().lower()

    try:
        validate_email(normalized, check_deliverability=False)
        return normalized
    except EmailNotValidError as exc:
        if LOCAL_EMAIL_PATTERN.fullmatch(normalized):
            return normalized
        raise ValueError(str(exc)) from exc
