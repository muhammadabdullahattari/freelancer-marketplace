from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: Optional[str] = Field(None, max_length=255)
    comment: Optional[str] = Field(None, max_length=5000)
    is_anonymous: bool = False


class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=255)
    comment: Optional[str] = Field(None, max_length=5000)


class ReviewResponse(BaseModel):
    id: UUID
    contract_id: UUID
    reviewer_id: UUID
    freelancer_id: UUID
    rating: int
    title: Optional[str]
    comment: Optional[str]
    is_anonymous: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReviewPublicResponse(BaseModel):
    id: UUID
    rating: int
    title: Optional[str]
    comment: Optional[str]
    is_anonymous: bool
    created_at: datetime
    reviewer_name: Optional[str] = None

    class Config:
        from_attributes = True


class ReviewsListPaginatedResponse(BaseModel):
    items: list[ReviewResponse]
    total: int
    skip: int
    limit: int
    average_rating: Optional[float]