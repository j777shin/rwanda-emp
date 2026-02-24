from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from models.chatbot import ChatbotResult, ChatbotStage
from middleware.auth import require_beneficiary


class EmploymentStatusUpdate(BaseModel):
    status: str  # "hired", "self-employed", or "none"
    hired_company_name: str | None = None
    self_employed_description: str | None = None

router = APIRouter()


async def _get_beneficiary(user: User, db: AsyncSession) -> Beneficiary:
    result = await db.execute(select(Beneficiary).where(Beneficiary.user_id == user.id))
    ben = result.scalar_one_or_none()
    if not ben:
        raise HTTPException(status_code=404, detail="Beneficiary profile not found")
    return ben


@router.get("")
async def get_dashboard(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    # Get chatbot progress
    chatbot_stages_result = await db.execute(
        select(ChatbotStage)
        .where(ChatbotStage.beneficiary_id == ben.id)
        .order_by(ChatbotStage.stage_number)
    )
    stages = chatbot_stages_result.scalars().all()

    chatbot_result = await db.execute(
        select(ChatbotResult).where(ChatbotResult.beneficiary_id == ben.id)
    )
    report = chatbot_result.scalar_one_or_none()

    return {
        "beneficiary": {
            "id": str(ben.id),
            "name": ben.name,
            "age": ben.age,
            "gender": ben.gender,
            "district": ben.district,
            "education_level": ben.education_level,
            "selection_status": ben.selection_status,
            "track": ben.track,
        },
        "phase1": {
            "skillcraft_score": float(ben.skillcraft_score) if ben.skillcraft_score else None,
            "skillcraft_completed": ben.skillcraft_score is not None,
            "pathways_completion_rate": float(ben.pathways_completion_rate) if ben.pathways_completion_rate else None,
            "pathways_enrolled": ben.pathways_user_id is not None,
            "business_dev_completed": ben.wants_entrepreneurship and bool(ben.business_development_text),
            "wants_entrepreneurship": ben.wants_entrepreneurship,
            "offline_attendance": ben.offline_attendance,
        },
        "phase2": {
            "selected": ben.selection_status == "selected",
            "track": ben.track,
            "chatbot_stages": [
                {
                    "stage_number": s.stage_number,
                    "stage_name": s.stage_name,
                    "status": s.status,
                }
                for s in stages
            ],
            "report_ready": report is not None,
            "self_employed": ben.self_employed,
            "hired": ben.hired,
            "hired_company_name": ben.hired_company_name or "",
            "self_employed_description": ben.self_employed_description or "",
        },
        "eligibility_score": float(ben.eligibility_score) if ben.eligibility_score else None,
    }


@router.post("/employment-status")
async def update_employment_status(
    payload: EmploymentStatusUpdate,
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    if payload.status == "hired":
        ben.hired = True
        ben.self_employed = False
        ben.hired_company_name = (payload.hired_company_name or "").strip()
        ben.self_employed_description = None
    elif payload.status == "self-employed":
        ben.self_employed = True
        ben.hired = False
        ben.self_employed_description = (payload.self_employed_description or "").strip()
        ben.hired_company_name = None
    else:
        ben.hired = False
        ben.self_employed = False
        ben.hired_company_name = None
        ben.self_employed_description = None

    await db.commit()
    return {"success": True, "status": payload.status}
