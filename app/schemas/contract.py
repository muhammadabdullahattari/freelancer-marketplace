from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class MilestoneResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    amount: float
    status: str
    order: int
    due_date: Optional[datetime]
    submitted_at: Optional[datetime]
    approved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ContractResponse(BaseModel):
    id: UUID
    job_id: UUID
    proposal_id: UUID
    client_id: UUID
    freelancer_id: UUID
    title: str
    description: Optional[str]
    total_amount: float
    amount_paid: float
    status: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    milestones: list[MilestoneResponse] = []

    class Config:
        from_attributes = True


class ContractListResponse(BaseModel):
    id: UUID
    title: str
    total_amount: float
    amount_paid: float
    status: str
    start_date: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class ContractsListPaginatedResponse(BaseModel):
    items: list[ContractListResponse]
    total: int
    skip: int
    limit: int