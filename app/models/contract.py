from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from sqlalchemy import Uuid
from uuid import UUID
import uuid
import enum
from app.models.base import SoftDeleteMixin

class ContractStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Contract(Base,SoftDeleteMixin):
    __tablename__ = "contracts"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    proposal_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    client_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    freelancer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("freelancer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[ContractStatus] = mapped_column(Enum(ContractStatus), default=ContractStatus.ACTIVE, nullable=False, index=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    job: Mapped["Job"] = relationship("Job", back_populates="contracts")
    proposal: Mapped["Proposal"] = relationship("Proposal", back_populates="contract")
    client: Mapped["User"] = relationship("User", foreign_keys=[client_id])
    freelancer: Mapped["FreelancerProfile"] = relationship("FreelancerProfile", back_populates="contracts", foreign_keys=[freelancer_id])
    milestones: Mapped[list["Milestone"]] = relationship("Milestone", back_populates="contract", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="contract", cascade="all, delete-orphan")