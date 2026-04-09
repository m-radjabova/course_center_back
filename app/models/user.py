import uuid
from sqlalchemy import Column, String, DateTime, Index, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    avatar = Column(String, nullable=True)
    hashed_password = Column(String(255), nullable=False)

    roles = Column(ARRAY(String), default=["teacher"], nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    refresh_token_hash = Column(String(255), nullable=True)

    __table_args__ = (
        Index("uq_users_email_lower", func.lower(email), unique=True),
    )
