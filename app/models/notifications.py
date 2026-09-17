from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from sqlalchemy import Uuid
from uuid import UUID
from enum import Enum
import uuid
import json


class NotificationEventType(str, Enum):
    USER_REGISTERED = "user_registered"
    SECURITY_EVENT = "security_event"
    PROPOSAL_RECEIVED = "proposal_received"
    PROPOSAL_ACCEPTED = "proposal_accepted"
    PROPOSAL_REJECTED = "proposal_rejected"
    CONTRACT_CREATED = "contract_created"
    MILESTONE_SUBMITTED = "milestone_submitted"
    MILESTONE_APPROVED = "milestone_approved"
    MILESTONE_REJECTED = "milestone_rejected"
    CONTRACT_COMPLETED = "contract_completed"
    REVIEW_SUBMITTED = "review_submitted"
    PAYMENT_RELEASED = "payment_released"


class NotificationStatus(str, Enum):
    PENDING = "pending"              
    SENT = "sent"                    
    FAILED = "failed"                
    BOUNCED = "bounced"              
    UNSUBSCRIBED = "unsubscribed"    
    DELIVERY_FAILED = "delivery_failed"  

class Notification(Base):

    __tablename__ = "notifications"
    
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # From NotificationEventType
    event_name: Mapped[str] = mapped_column(String(100), nullable=False)  # Human-readable name
    resource_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)  # job_id, proposal_id, etc
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # job, proposal, contract, milestone, review
    recipient_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_by_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", 
                                                                                             ondelete="SET NULL"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    email_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email_body_html: Mapped[str] = mapped_column(Text, nullable=False) 
    event_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)  
    status: Mapped[str] = mapped_column(String(50), default=NotificationStatus.PENDING.value, nullable=False, index=True)
    delivery_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    was_preference_skipped: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    skip_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    

    recipient_user: Mapped["User"] = relationship("User", foreign_keys=[recipient_user_id], backref="notifications_received")
    triggered_by_user: Mapped["User | None"] = relationship("User", foreign_keys=[triggered_by_user_id])
    
    def __repr__(self):
        return f"<Notification {self.event_type} to {self.recipient_user_id} status={self.status}>"