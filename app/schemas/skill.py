from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Union
from enum import Enum

class ProficiencyLevel(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    EXPERT = "EXPERT"

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
    proficiency_level: ProficiencyLevel = ProficiencyLevel.INTERMEDIATE


class FreelancerSkillResponse(BaseModel):
    id: Union[UUID, int]
    skill: SkillResponse
    proficiency_level: str
    created_at: datetime

    class Config:
        from_attributes = True