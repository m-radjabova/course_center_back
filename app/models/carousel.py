from sqlalchemy import Column, DateTime, String, func
from app.core.database import Base


class Carousel(Base):
    __tablename__ = "carousels"

    id = Column(String, primary_key=True, index=True)
    title1 = Column(String(100), nullable=False)
    title2 = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    img = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    

