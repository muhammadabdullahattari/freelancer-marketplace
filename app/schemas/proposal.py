from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class ProposalCreate(BaseModel):
    cover_letter: str = Field(min_length=20, max_length=5000)
    proposed_rate: float = Field(gt=0)
    estimated_duration: Optional[str] = Field(None, max_length=100)


class ProposalResponse(BaseModel):
    id: UUID
    job_id: UUID
    freelancer_id: UUID
    cover_letter: str
    proposed_rate: float
    estimated_duration: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    accepted_at: Optional[datetime]
    rejected_at: Optional[datetime]

    class Config:
        from_attributes = True


class ProposalDetailResponse(ProposalResponse):
    job_title: Optional[str] = None
    freelancer_name: Optional[str] = None

    class Config:
        from_attributes = True


class ProposalsListPaginatedResponse(BaseModel):
    items: list[ProposalResponse]
    total: int
    skip: int
    limit: int