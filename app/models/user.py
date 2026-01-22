from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    role = Column(String(20), default="user", nullable=False) 

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    refresh_token_hash = Column(String(255), nullable=True)

    posts = relationship(
        "Post",
        back_populates="user",
        cascade="all, delete"
    )

    todos = relationship(
        "Todo",
        back_populates="user",
        cascade="all, delete"
    )

    