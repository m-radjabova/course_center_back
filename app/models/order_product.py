from sqlalchemy import Column, Integer, Numeric, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class OrderProduct(Base):
    __tablename__ = "order_products"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    order = relationship("Order", back_populates="products")

    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    product = relationship("Product")

    price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    total_price = Column(Numeric(10, 2), nullable=False)

    name = Column(String(255), nullable=False)
    image = Column(String(500), nullable=True)
    weight = Column(String(50), nullable=True)
    rating = Column(Float, nullable=True)
    description = Column(String(1000), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
