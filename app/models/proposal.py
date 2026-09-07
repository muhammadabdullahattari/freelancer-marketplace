from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from sqlalchemy import Uuid
from uuid import UUID
import uuid
import enum


class ProposalStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    freelancer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("freelancer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    cover_letter: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_rate: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_duration: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[ProposalStatus] = mapped_column(Enum(ProposalStatus), default=ProposalStatus.SUBMITTED, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    job: Mapped["Job"] = relationship("Job", back_populates="proposals")
    freelancer: Mapped["FreelancerProfile"] = relationship("FreelancerProfile", back_populates="proposals", foreign_keys=[freelancer_id])
    contract: Mapped["Contract"] = relationship("Contract", back_populates="proposal", uselist=False)