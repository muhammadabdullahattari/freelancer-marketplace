from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from sqlalchemy import Uuid
from uuid import UUID
import uuid


class FileUpload(Base):
    """Track uploaded files"""
    __tablename__ = "file_uploads"
    
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # profile_picture, proposal_attachment, etc
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    storage_bucket: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    uploaded_by_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)  # Profile picture
    proposal_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("proposals.id", ondelete="CASCADE"), nullable=True, index=True)  # Proposal attachment
    contract_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=True, index=True)  # Contract document
    milestone_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("milestones.id", ondelete="CASCADE"), nullable=True, index=True)  # Milestone deliverable
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    uploaded_by_user: Mapped["User"] = relationship("User", foreign_keys=[uploaded_by_user_id])