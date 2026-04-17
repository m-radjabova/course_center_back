from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class ServiceError(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class BaseService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def not_found(entity: str) -> ServiceError:
        return ServiceError(status.HTTP_404_NOT_FOUND, f"{entity} not found")

    @staticmethod
    def bad_request(message: str) -> ServiceError:
        return ServiceError(status.HTTP_400_BAD_REQUEST, message)

    @staticmethod
    def forbidden(message: str) -> ServiceError:
        return ServiceError(status.HTTP_403_FORBIDDEN, message)

    def commit(self):
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise self.bad_request("Database constraint violated") from exc

    def refresh(self, instance):
        self.db.refresh(instance)
        return instance


def parse_uuid(value: str | UUID, field_name: str = "id") -> UUID:
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise ServiceError(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Invalid {field_name}") from exc
