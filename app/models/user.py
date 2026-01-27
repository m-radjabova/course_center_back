import uuid
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.order import Order


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    name = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    roles = Column(ARRAY(String), default=["user"], nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    refresh_token_hash = Column(String(255), nullable=True)

    orders = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")


