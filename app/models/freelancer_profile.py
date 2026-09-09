from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from sqlalchemy import Uuid
from uuid import UUID
from app.models.base import SoftDeleteMixin
import uuid

class FreelancerProfile(Base,SoftDeleteMixin):
    __tablename__ = "freelancer_profiles"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(String(150), nullable=True)
    hourly_rate: Mapped[float | None] = mapped_column(Float, nullable=True) 
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    total_earnings: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_hours_worked: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)    
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    skills: Mapped[list["FreelancerSkill"]] = relationship("FreelancerSkill", back_populates="freelancer", cascade="all, delete-orphan")
    proposals: Mapped[list["Proposal"]] = relationship("Proposal", back_populates="freelancer", foreign_keys="Proposal.freelancer_id")
    contracts: Mapped[list["Contract"]] = relationship("Contract", back_populates="freelancer", foreign_keys="Contract.freelancer_id")
    reviews_received: Mapped[list["Review"]] = relationship("Review", back_populates="freelancer", foreign_keys="Review.freelancer_id")