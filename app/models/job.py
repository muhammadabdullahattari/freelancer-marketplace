from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from sqlalchemy import Uuid
from uuid import UUID
import uuid
import enum


class JobStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"
    COMPLETED = "COMPLETED"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False) 
    budget_type: Mapped[str] = mapped_column(default="FIXED", nullable=False)  
    budget_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.DRAFT, nullable=False, index=True)
    duration_estimate: Mapped[str | None] = mapped_column(String(50), nullable=True)  
    experience_level: Mapped[str] = mapped_column(default="INTERMEDIATE", nullable=False)  
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client: Mapped["User"] = relationship("User", foreign_keys=[client_id])
    skills: Mapped[list["JobSkill"]] = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    proposals: Mapped[list["Proposal"]] = relationship("Proposal", back_populates="job", cascade="all, delete-orphan")
    contracts: Mapped[list["Contract"]] = relationship("Contract", back_populates="job", cascade="all, delete-orphan")