from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class JobSkillResponse(BaseModel):
    id: int
    skill_id: UUID
    skill_name: str

    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    description: str = Field(min_length=20)
    budget_type: str = Field(default="FIXED")  # FIXED or HOURLY
    budget_min: Optional[float] = Field(None, ge=0)
    budget_max: Optional[float] = Field(None, ge=0)
    duration_estimate: Optional[str] = Field(None, max_length=50)
    experience_level: str = Field(default="INTERMEDIATE")
    skill_ids: list[UUID] = []


class JobUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=20)
    budget_type: Optional[str] = None
    budget_min: Optional[float] = Field(None, ge=0)
    budget_max: Optional[float] = Field(None, ge=0)
    duration_estimate: Optional[str] = Field(None, max_length=50)
    experience_level: Optional[str] = None
    skill_ids: Optional[list[UUID]] = None


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