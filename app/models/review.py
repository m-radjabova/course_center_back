from sqlalchemy import UUID, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    rating = Column(Integer, nullable=False)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="reviews")

    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    product = relationship("Product", back_populates="reviews")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
