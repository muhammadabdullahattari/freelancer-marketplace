from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from sqlalchemy import Uuid
from uuid import UUID
import uuid


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    freelancer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("freelancer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_anonymous: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    contract: Mapped["Contract"] = relationship("Contract", back_populates="reviews")
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewer_id])
    freelancer: Mapped["FreelancerProfile"] = relationship("FreelancerProfile", back_populates="reviews_received", foreign_keys=[freelancer_id])