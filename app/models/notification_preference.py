from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from sqlalchemy import Uuid
from uuid import UUID
import uuid


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True,index=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    transactional_emails: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Critical events
    proposal_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    contract_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    milestone_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    review_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    marketing_emails: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # Opt-in
    digest_frequency: Mapped[str] = mapped_column(String(50), default="instant", nullable=False)  # instant, daily, weekly
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<NotificationPreference user_id={self.user_id}>"