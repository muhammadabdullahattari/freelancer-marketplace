from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class SkillCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class SkillUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class SkillResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FreelancerSkillCreate(BaseModel):
    skill_id: UUID
    proficiency_level: str = Field(default="INTERMEDIATE")
    years_experience: Optional[int] = Field(None, ge=0)


class FreelancerSkillResponse(BaseModel):
    id: int
    skill: SkillResponse
    proficiency_level: str
    years_experience: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True