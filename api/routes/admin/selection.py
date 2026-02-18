from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from middleware.auth import require_admin
from services.selection import calculate_all_pmt_scores, select_phase1_beneficiaries, assign_tracks

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
    # Get counts by selection status
    status_counts = {}
    for status in ["pending", "selected", "rejected", "waitlist"]:
        result = await db.execute(
            select(func.count()).select_from(Beneficiary).where(Beneficiary.selection_status == status)
        )
        status_counts[status] = result.scalar()

    # Get counts by track
    track_counts = {}
    for track in ["employment", "entrepreneurship"]:
        result = await db.execute(
            select(func.count()).select_from(Beneficiary).where(Beneficiary.track == track)
        )
        track_counts[track] = result.scalar()

    # Avg eligibility scores
    result = await db.execute(
        select(func.avg(Beneficiary.eligibility_score)).where(Beneficiary.selection_status == "selected")
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


@router.get("/eligibility/stats")
async def get_eligibility_stats(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Score distribution in buckets
    buckets = []
    ranges = [(0, 12), (12, 12.5), (12.5, 13), (13, 13.5), (13.5, 14), (14, 100)]
    for low, high in ranges:
        result = await db.execute(
            select(func.count()).select_from(Beneficiary)
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
        ).where(Beneficiary.eligibility_score.is_not(None))
    )
    row = result.one()

    return {
        "distribution": buckets,
        "min_score": float(row[0]) if row[0] else None,
        "max_score": float(row[1]) if row[1] else None,
        "avg_score": float(row[2]) if row[2] else None,
        "total_scored": row[3],
    }
