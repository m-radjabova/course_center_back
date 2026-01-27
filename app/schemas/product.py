from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: int
    category_id: int
    weight: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[int] = None
    category_id: Optional[int] = None
    weight: Optional[str] = None
    rating: Optional[int] = None


class ProductOut(ProductBase):
    id: str
    image: Optional[str] = None
    rating: int
    created_at: datetime

    class Config:
        from_attributes = True
