from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from sqlalchemy import Uuid
from uuid import UUID


import uuid


class FreelancerSkill(Base):
    __tablename__ = "freelancer_skills"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    freelancer_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("freelancer_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    proficiency_level: Mapped[str] = mapped_column(default="INTERMEDIATE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    freelancer: Mapped["FreelancerProfile"] = relationship("FreelancerProfile", back_populates="skills")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="freelancers")