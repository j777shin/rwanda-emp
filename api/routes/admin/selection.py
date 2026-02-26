from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from models.survey import SurveyResponse
from models.chatbot import ChatbotConversation, ChatbotStage, ChatbotResult
from middleware.auth import require_admin
from services.selection import (
    calculate_all_pmt_scores,
    select_phase1_beneficiaries,
    assign_tracks,
    apply_phase1_results,
    run_phase2_selection,
)
from utils.helpers import TEST_ACCOUNT_EMAILS, test_account_user_ids_subquery

router = APIRouter()


class Phase1SelectionRequest(BaseModel):
    count: int = 9000


class TrackAssignmentRequest(BaseModel):
    beneficiary_ids: list[str]
    track: str  # "employment" or "entrepreneurship"


@router.post("/calculate-scores")
async def run_pmt_scoring(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await calculate_all_pmt_scores(db)
    return {"message": "PMT scoring complete", **result}


@router.post("/phase1")
async def run_phase1_selection(
    body: Phase1SelectionRequest,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await select_phase1_beneficiaries(db, body.count)
    return {"message": "Phase 1 selection complete", **result}


@router.get("/results")
async def get_selection_results(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())

    # Get counts by selection status
    status_counts = {}
    for status in ["pending", "selected", "rejected", "waitlist"]:
        result = await db.execute(
            select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.selection_status == status)
        )
        status_counts[status] = result.scalar()

    # Get counts by track
    track_counts = {}
    for track in ["employment", "entrepreneurship"]:
        result = await db.execute(
            select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.track == track)
        )
        track_counts[track] = result.scalar()

    # Avg eligibility scores
    result = await db.execute(
        select(func.avg(Beneficiary.eligibility_score)).where(exc, Beneficiary.selection_status == "selected")
    )
    avg_selected_score = result.scalar()

    return {
        "status_counts": status_counts,
        "track_counts": track_counts,
        "avg_selected_score": float(avg_selected_score) if avg_selected_score else None,
    }


@router.post("/phase2")
async def assign_phase2_tracks(
    body: TrackAssignmentRequest,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if body.track not in ("employment", "entrepreneurship"):
        return {"error": "Track must be 'employment' or 'entrepreneurship'"}

    result = await assign_tracks(db, body.beneficiary_ids, body.track)
    return {"message": "Track assignment complete", **result}


@router.post("/apply-phase1-results")
async def apply_phase1_training_results(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await apply_phase1_results(db)
    return {"message": "Phase 1 results applied", **result}


@router.post("/run-phase2")
async def run_phase2_auto_selection(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await run_phase2_selection(db)
    return {"message": "Phase 2 selection complete", **result}


@router.post("/reset")
async def reset_selection(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reset eligibility scores and selection status for all non-test beneficiaries."""
    # Get test account user IDs to exclude
    test_user_result = await db.execute(
        select(User.id).where(User.email.in_(TEST_ACCOUNT_EMAILS))
    )
    test_user_ids = [row[0] for row in test_user_result.all()]

    # Reset all non-test beneficiaries
    stmt = (
        update(Beneficiary)
        .where(Beneficiary.user_id.not_in(test_user_ids) if test_user_ids else True)
        .values(
            eligibility_score=None,
            selection_status="pending",
            track=None,
        )
    )
    result = await db.execute(stmt)
    await db.commit()

    return {"message": "Selection reset complete", "reset_count": result.rowcount}


@router.post("/reset-phase2")
async def reset_phase2_selection(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reset track assignments and generated Phase 1 results for all non-test selected beneficiaries."""
    # Get test account user IDs to exclude
    test_user_result = await db.execute(
        select(User.id).where(User.email.in_(TEST_ACCOUNT_EMAILS))
    )
    test_user_ids = [row[0] for row in test_user_result.all()]

    # Reset all generated Phase 1 results and track assignments for selected beneficiaries
    stmt = (
        update(Beneficiary)
        .where(
            Beneficiary.user_id.not_in(test_user_ids) if test_user_ids else True,
            Beneficiary.selection_status == "selected",
        )
        .values(
            track=None,
            skillcraft_score=None,
            w_score=None,
            e_score=None,
            skillcraft_scores=None,
            ingazi_completion_rate=None,
            offline_attendance=0,
            wants_entrepreneurship=False,
            business_development_text=None,
            grant_received=False,
            grant_amount=0,
            hired=False,
            self_employed=False,
            hired_company_name=None,
            self_employed_description=None,
            phase1_satisfactory=None,
            emp_track_satisfactory=None,
            ent_track_satisfactory=None,
        )
    )
    result = await db.execute(stmt)

    # Get non-test selected beneficiary IDs for related data cleanup
    non_test_ben_ids = await db.execute(
        select(Beneficiary.id).where(
            Beneficiary.user_id.not_in(test_user_ids) if test_user_ids else True,
            Beneficiary.selection_status == "selected",
        )
    )
    ben_ids = [row[0] for row in non_test_ben_ids.all()]
    if ben_ids:
        # Delete all survey responses (phase1, employment, entrepreneurship)
        await db.execute(
            delete(SurveyResponse).where(
                SurveyResponse.beneficiary_id.in_(ben_ids),
            )
        )
        # Delete chatbot data
        await db.execute(
            delete(ChatbotConversation).where(
                ChatbotConversation.beneficiary_id.in_(ben_ids),
            )
        )
        await db.execute(
            delete(ChatbotStage).where(
                ChatbotStage.beneficiary_id.in_(ben_ids),
            )
        )
        await db.execute(
            delete(ChatbotResult).where(
                ChatbotResult.beneficiary_id.in_(ben_ids),
            )
        )

    await db.commit()

    return {"message": "Phase 2 reset complete — all generated data cleared", "reset_count": result.rowcount}


@router.get("/eligibility/stats")
async def get_eligibility_stats(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())

    # Score distribution in buckets
    buckets = []
    ranges = [(0, 12), (12, 12.5), (12.5, 13), (13, 13.5), (13.5, 14), (14, 100)]
    for low, high in ranges:
        result = await db.execute(
            select(func.count()).select_from(Beneficiary)
            .where(exc)
            .where(Beneficiary.eligibility_score >= low)
            .where(Beneficiary.eligibility_score < high)
            .where(Beneficiary.eligibility_score.is_not(None))
        )
        buckets.append({"range": f"{low}-{high}", "count": result.scalar()})

    # Overall stats
    result = await db.execute(
        select(
            func.min(Beneficiary.eligibility_score),
            func.max(Beneficiary.eligibility_score),
            func.avg(Beneficiary.eligibility_score),
            func.count(),
        ).where(exc, Beneficiary.eligibility_score.is_not(None))
    )
    row = result.one()

    return {
        "distribution": buckets,
        "min_score": float(row[0]) if row[0] else None,
        "max_score": float(row[1]) if row[1] else None,
        "avg_score": float(row[2]) if row[2] else None,
        "total_scored": row[3],
    }
