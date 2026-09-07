from datetime import datetime, timezone
from sqlalchemy import Boolean,DateTime,Integer,String,Text
from sqlalchemy.orm import Mapped, mapped_column , relationship
from app.database import Base
from sqlalchemy import Uuid
from uuid import UUID
import uuid

class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(30),unique=True,index=True,nullable=False)
    name: Mapped[str] = mapped_column(String(100),nullable=False)
    email: Mapped[str] = mapped_column(String(255),unique=True,index=True,nullable=False)

    first_name: Mapped[str | None] = mapped_column(String(50),nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(50),nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20),nullable=True)

    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean,default=True,nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean,default=False,nullable=False)
    

    failed_login_attempts: Mapped[int] = mapped_column(Integer,default=0,nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),nullable=True,)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(45),nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),default=lambda: datetime.now(timezone.utc),onupdate=lambda: datetime.now(timezone.utc),nullable=False)
    
    role: Mapped[str] = mapped_column(String(20), default="CLIENT", nullable=False)
    sessions: Mapped[list["UserSession"]] = relationship("UserSession",back_populates="user",cascade="all, delete-orphan")