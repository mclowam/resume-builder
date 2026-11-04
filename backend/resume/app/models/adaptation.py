import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Adaptation(Base):
    __tablename__ = "adaptations"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'running', 'done', 'failed')", name="ck_adaptations_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), index=True)
    resume_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resumes.id"))
    vacancy_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vacancies.id"))
    status: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending")
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
