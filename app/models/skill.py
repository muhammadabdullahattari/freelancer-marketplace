from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from sqlalchemy import Uuid
from uuid import UUID
import uuid


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    freelancers: Mapped[list["FreelancerSkill"]] = relationship("FreelancerSkill", back_populates="skill", cascade="all, delete-orphan")
    jobs: Mapped[list["JobSkill"]] = relationship("JobSkill", back_populates="skill", cascade="all, delete-orphan")