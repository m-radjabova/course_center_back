from sqlalchemy import Column, Integer, Numeric, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="orders")

    total_price = Column(Numeric(10, 2), nullable=False)

    status = Column(String(30), default="pending", nullable=False)
    payment_method = Column(String(50), nullable=False)

    shipping_address = Column(String(255), nullable=False)
    notes = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    delivery_date = Column(DateTime, nullable=True)

    location = Column(JSON, nullable=True)
    

    products = relationship(
        "OrderProduct",
        back_populates="order",
        cascade="all, delete-orphan"
    )
