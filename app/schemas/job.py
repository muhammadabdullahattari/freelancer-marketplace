from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID
from enum import Enum
from typing import Optional, Union
from app.schemas.skill import SkillResponse


class ProficiencyLevel(str, Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    EXPERT = "EXPERT"

class BudgetType(str, Enum):
    FIXED = "FIXED"
    HOURLY = "HOURLY"

class JobSkillResponse(BaseModel):
    id: Union[UUID, int]
    skill: SkillResponse

    class Config:
        from_attributes = True

class JobCreate(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    description: str = Field(min_length=20)
    budget_type: BudgetType = BudgetType.FIXED  
    budget_min: Optional[float] = Field(None, ge=1)
    budget_max: Optional[float] = Field(None, ge=1)
    duration_estimate: Optional[str] = Field(None, max_length=50)
    experience_level: ProficiencyLevel = ProficiencyLevel.BEGINNER
    skill_ids: list[UUID] = []
    
    @field_validator("skill_ids")
    @classmethod
    def validate_unique_skills(cls, v: Optional[list[UUID]]) -> Optional[list[UUID]]:
        if v is not None and len(v) != len(set(v)):
            raise ValueError("Duplicate skill_ids are not allowed")
        return v


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: BudgetType = BudgetType.FIXED 
    budget_type: Optional[str] = None
    budget_min: Optional[float] = Field(None, ge=1)
    budget_max: Optional[float] = Field(None, ge=1)
    duration_estimate: Optional[str] = Field(None, max_length=50)
    experience_level: ProficiencyLevel = ProficiencyLevel.BEGINNER
    skill_ids: Optional[list[UUID]] = None
    
    @field_validator("skill_ids")
    @classmethod
    def validate_unique_skills(cls, v: Optional[list[UUID]]) -> Optional[list[UUID]]:
        if v is not None and len(v) != len(set(v)):
            raise ValueError("Duplicate skill_ids are not allowed")
        return v


class JobResponse(BaseModel):
    id: UUID
    client_id: UUID
    title: str
    description: str
    budget_type: str
    budget_min: Optional[float]
    budget_max: Optional[float]
    status: str
    duration_estimate: Optional[str]
    experience_level: str
    is_active: bool
    skills: list[JobSkillResponse] = []
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]
    closed_at: Optional[datetime]

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    id: UUID
    title: str
    budget_type: str
    budget_max: Optional[float]
    status: str
    experience_level: str
    created_at: datetime
    skills: list[JobSkillResponse] = []

    class Config:
        from_attributes = True


class JobsListPaginatedResponse(BaseModel):
    items: list[JobListResponse]
    total: int
    skip: int
    limit: int