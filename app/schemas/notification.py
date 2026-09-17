from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class NotificationResponse(BaseModel):
    id: UUID
    event_type: str
    subject: str
    body_html: str
    status: str
    created_at: datetime
    delivered_at: Optional[datetime]
    delivery_attempts: int
    last_error: Optional[str]
    
    class Config:
        from_attributes = True


class NotificationItemResponse(BaseModel):
    id: UUID
    event_type: str
    subject: str
    status: str
    created_at: datetime
    delivered_at: Optional[datetime]
    skip_reason: Optional[str]
    
    class Config:
        from_attributes = True


class NotificationHistoryPaginatedResponse(BaseModel):
    items: List[NotificationItemResponse]
    total: int
    pages: int
    skip: int
    limit: int


class NotificationPreferenceResponse(BaseModel):
    id: UUID
    email_enabled: bool
    transactional_emails: bool
    proposal_notifications: bool
    contract_notifications: bool
    milestone_notifications: bool
    review_notifications: bool
    marketing_emails: bool
    digest_frequency: str
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NotificationPreferenceUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    transactional_emails: Optional[bool] = None
    proposal_notifications: Optional[bool] = None
    contract_notifications: Optional[bool] = None
    milestone_notifications: Optional[bool] = None
    review_notifications: Optional[bool] = None
    marketing_emails: Optional[bool] = None
    digest_frequency: Optional[str] = None