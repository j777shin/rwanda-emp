import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    beneficiary_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("beneficiaries.id", ondelete="CASCADE"), nullable=False)
    survey_type: Mapped[str] = mapped_column(String(50), nullable=False)
    responses: Mapped[dict] = mapped_column(JSON, nullable=False)
    completion_time: Mapped[int | None] = mapped_column(Integer)  # in seconds
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    beneficiary: Mapped["Beneficiary"] = relationship(back_populates="survey_responses")
