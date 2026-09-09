from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class SkillResponse(BaseModel):
    id: UUID
    name: str
    proficiency_level: str
    years_experience: Optional[int] = None

    class Config:
        from_attributes = True


class FreelancerProfileCreate(BaseModel):
    bio: Optional[str] = Field(None, max_length=5000)
    title: Optional[str] = Field(None, max_length=150)
    hourly_rate: Optional[float] = Field(None, ge=0)
    years_experience: Optional[int] = Field(None, ge=0)
    is_available: bool = True


class FreelancerProfileUpdate(BaseModel):
    bio: Optional[str] = Field(None, max_length=5000)
    title: Optional[str] = Field(None, max_length=150)
    hourly_rate: Optional[float] = Field(None, ge=0)
    years_experience: Optional[int] = Field(None, ge=0)
    is_available: Optional[bool] = None


class FreelancerProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    bio: Optional[str]
    title: Optional[str]
    hourly_rate: Optional[float]
    years_experience: Optional[int]
    is_available: bool
    total_earnings: float
    total_hours_worked: float
    average_rating: Optional[float]
    total_reviews: int
    skills: list[SkillResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True