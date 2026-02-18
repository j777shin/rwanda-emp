from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from models.survey import SurveyResponse
from middleware.auth import require_beneficiary

router = APIRouter()


class SurveySubmission(BaseModel):
    responses: dict  # JSON object of question_id -> answer


async def _get_beneficiary(user: User, db: AsyncSession) -> Beneficiary:
    result = await db.execute(select(Beneficiary).where(Beneficiary.user_id == user.id))
    ben = result.scalar_one_or_none()
    if not ben:
        raise HTTPException(status_code=404, detail="Beneficiary profile not found")
    return ben


async def _save_survey_response(
    db: AsyncSession, beneficiary_id, survey_type: str, responses: dict
):
    """Save or update a survey response in the survey_responses table."""
    result = await db.execute(
        select(SurveyResponse).where(
            SurveyResponse.beneficiary_id == beneficiary_id,
            SurveyResponse.survey_type == survey_type,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.responses = responses
        existing.completed_at = datetime.utcnow()
    else:
        survey = SurveyResponse(
            beneficiary_id=beneficiary_id,
            survey_type=survey_type,
            responses=responses,
            completed_at=datetime.utcnow(),
        )
        db.add(survey)


@router.post("/phase1")
async def submit_phase1_survey(
    body: SurveySubmission,
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    # Calculate average satisfaction from responses (values expected as 1-5 ratings)
    ratings = [v for v in body.responses.values() if isinstance(v, (int, float))]
    avg_score = sum(ratings) / len(ratings) * 20 if ratings else 0  # Scale to 0-100

    ben.phase1_satisfactory = avg_score

    # Also save to survey_responses table for admin analytics
    await _save_survey_response(db, ben.id, "phase1", body.responses)

    await db.commit()

    return {"message": "Phase 1 survey submitted", "score": avg_score}


@router.post("/employment")
async def submit_employment_survey(
    body: SurveySubmission,
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    ratings = [v for v in body.responses.values() if isinstance(v, (int, float))]
    avg_score = sum(ratings) / len(ratings) * 20 if ratings else 0

    ben.emp_track_satisfactory = avg_score

    await _save_survey_response(db, ben.id, "employment", body.responses)

    await db.commit()

    return {"message": "Employment survey submitted", "score": avg_score}


@router.post("/entrepreneurship")
async def submit_entrepreneurship_survey(
    body: SurveySubmission,
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    ratings = [v for v in body.responses.values() if isinstance(v, (int, float))]
    avg_score = sum(ratings) / len(ratings) * 20 if ratings else 0

    ben.ent_track_satisfactory = avg_score

    await _save_survey_response(db, ben.id, "entrepreneurship", body.responses)

    await db.commit()

    return {"message": "Entrepreneurship survey submitted", "score": avg_score}


@router.get("/status")
async def get_survey_status(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    return {
        "phase1_completed": ben.phase1_satisfactory is not None,
        "phase1_score": float(ben.phase1_satisfactory) if ben.phase1_satisfactory else None,
        "employment_completed": ben.emp_track_satisfactory is not None,
        "employment_score": float(ben.emp_track_satisfactory) if ben.emp_track_satisfactory else None,
        "entrepreneurship_completed": ben.ent_track_satisfactory is not None,
        "entrepreneurship_score": float(ben.ent_track_satisfactory) if ben.ent_track_satisfactory else None,
    }
