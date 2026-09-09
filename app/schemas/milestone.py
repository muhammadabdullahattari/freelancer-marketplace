from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    amount: float = Field(gt=0)
    due_date: Optional[datetime] = None
    order: int = Field(default=0, ge=0)


class MilestoneUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    amount: Optional[float] = Field(None, gt=0)
    due_date: Optional[datetime] = None
    order: Optional[int] = Field(None, ge=0)


class MilestoneResponse(BaseModel):
    id: UUID
    contract_id: UUID
    title: str
    description: Optional[str]
    amount: float
    status: str
    order: int
    due_date: Optional[datetime]
    submitted_at: Optional[datetime]
    approved_at: Optional[datetime]
    rejected_at: Optional[datetime]
    payment_released_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=5, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    amount: float = Field(gt=0)
    due_date: Optional[datetime] = None
    order: int = Field(default=0, ge=0)


class MilestoneUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    amount: Optional[float] = Field(None, gt=0)
    due_date: Optional[datetime] = None
    order: Optional[int] = Field(None, ge=0)


class MilestoneResponse(BaseModel):
    id: UUID
    contract_id: UUID
    title: str
    description: Optional[str]
    amount: float
    status: str
    order: int
    due_date: Optional[datetime]
    submitted_at: Optional[datetime]
    approved_at: Optional[datetime]
    rejected_at: Optional[datetime]
    payment_released_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True