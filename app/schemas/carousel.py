from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CarouselCreate(BaseModel):
    title1: str = Field(min_length=1, max_length=100)
    title2: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


class CarouselUpdate(BaseModel):
    title1: Optional[str] = Field(default=None, min_length=1, max_length=100)
    title2: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)


class CarouselOut(BaseModel):
    id: str
    title1: str
    title2: str
    description: Optional[str] = None
    img: str
    created_at: datetime

    class Config:
        from_attributes = True
