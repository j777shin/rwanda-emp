import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Boolean, Integer, DateTime, Numeric, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    # Personal Information
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str | None] = mapped_column(String(10))
    contact: Mapped[str | None] = mapped_column(String(50))

    # Household Information
    marriage_status: Mapped[bool] = mapped_column(Boolean, default=False)
    disability: Mapped[bool] = mapped_column(Boolean, default=False)
    education_level: Mapped[str | None] = mapped_column(String(30))
    occupation: Mapped[bool] = mapped_column(Boolean, default=False)
    informal_working: Mapped[bool] = mapped_column(Boolean, default=False)

    # Livestock Assets
    num_goats: Mapped[int] = mapped_column(Integer, default=0)
    num_sheep: Mapped[int] = mapped_column(Integer, default=0)
    num_pigs: Mapped[int] = mapped_column(Integer, default=0)

    # Land & Housing
    land_ownership: Mapped[bool] = mapped_column(Boolean, default=False)
    land_size: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), default=0)
    num_radio: Mapped[int] = mapped_column(Integer, default=0)
    num_phone: Mapped[int] = mapped_column(Integer, default=0)
    num_tv: Mapped[int] = mapped_column(Integer, default=0)

    # Cooking, floor, lighting (PMT variables)
    cooking_firewood: Mapped[bool] = mapped_column(Boolean, default=False)
    cooking_gas: Mapped[bool] = mapped_column(Boolean, default=False)
    cooking_charcoal: Mapped[bool] = mapped_column(Boolean, default=False)
    floor_earth_sand: Mapped[bool] = mapped_column(Boolean, default=False)
    floor_tiles: Mapped[bool] = mapped_column(Boolean, default=False)
    lighting: Mapped[bool] = mapped_column(Boolean, default=False)

    # Livestock (PMT)
    num_cattle: Mapped[int] = mapped_column(Integer, default=0)

    # Household (PMT variables)
    children_under_18: Mapped[int] = mapped_column(Integer, default=0)
    household_size: Mapped[int] = mapped_column(Integer, default=0)
    hh_head_university: Mapped[bool] = mapped_column(Boolean, default=False)
    hh_head_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    hh_head_secondary: Mapped[bool] = mapped_column(Boolean, default=False)
    hh_head_married: Mapped[bool] = mapped_column(Boolean, default=False)
    hh_head_widow: Mapped[bool] = mapped_column(Boolean, default=False)
    hh_head_divorced: Mapped[bool] = mapped_column(Boolean, default=False)
    hh_head_female: Mapped[bool] = mapped_column(Boolean, default=False)

    # District
    district: Mapped[str | None] = mapped_column(String(30))

    # SkillCraft & Pathways
    skillcraft_user_id: Mapped[str | None] = mapped_column(String(100))
    skillcraft_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    skillcraft_last_sync: Mapped[datetime | None] = mapped_column(DateTime)
    pathways_user_id: Mapped[str | None] = mapped_column(String(100))
    pathways_completion_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    pathways_last_sync: Mapped[datetime | None] = mapped_column(DateTime)
    pathways_course_progress: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Selection & Track
    eligibility_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    selection_status: Mapped[str] = mapped_column(String(20), default="pending")
    track: Mapped[str | None] = mapped_column(String(20))

    # Employment / programme outcomes
    self_employed: Mapped[bool] = mapped_column(Boolean, default=False)
    hired: Mapped[bool] = mapped_column(Boolean, default=False)
    hired_company_name: Mapped[str | None] = mapped_column(String(255))
    self_employed_description: Mapped[str | None] = mapped_column(Text)
    offline_attendance: Mapped[int] = mapped_column(Integer, default=0)
    phase1_satisfactory: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    emp_track_satisfactory: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    ent_track_satisfactory: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # Grant
    grant_received: Mapped[bool] = mapped_column(Boolean, default=False)
    grant_amount: Mapped[int] = mapped_column(Integer, default=0)

    # Business development (new columns)
    business_development_text: Mapped[str | None] = mapped_column(Text)
    wants_entrepreneurship: Mapped[bool] = mapped_column(Boolean, default=False)

    # Manual entry flag (True = registered via admin portal, deleted on admin logout)
    is_manual_entry: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="beneficiary")
    chatbot_conversations: Mapped[list["ChatbotConversation"]] = relationship(back_populates="beneficiary")
    chatbot_result: Mapped["ChatbotResult"] = relationship(back_populates="beneficiary", uselist=False)
    chatbot_stages: Mapped[list["ChatbotStage"]] = relationship(back_populates="beneficiary")
    survey_responses: Mapped[list["SurveyResponse"]] = relationship(back_populates="beneficiary")
