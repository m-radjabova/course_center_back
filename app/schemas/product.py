
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

class ProductCreate(BaseModel):
    name: str
    price: int
    category_id: int
    description: str | None = None
    weight: str | None = None

class ProductUpdate(BaseModel):
    name: str | None = None
    price: int | None = None
    category_id: int | None = None
    description: str | None = None
    weight: str | None = None

class ProductOut(BaseModel):
    id: str
    name: str
    description: str | None
    price: int
    category_id: int
    image: str | None
    weight: str | None

    rating: float         
    rating_count: int      
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewOut(BaseModel):
    id: int
    title: str
    rating: int
    user_id: UUID
    product_id: str
    created_at: datetime

    class Config:
        from_attributes = True 

class ReviewCreate(BaseModel):
    title: str = Field(..., max_length=255)
    rating: int = Field(..., ge=1, le=5)