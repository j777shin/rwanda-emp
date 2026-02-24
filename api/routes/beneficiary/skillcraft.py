from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from middleware.auth import require_beneficiary
from services.skillcraft import skillcraft_service

router = APIRouter()


async def _get_beneficiary(user: User, db: AsyncSession) -> Beneficiary:
    result = await db.execute(select(Beneficiary).where(Beneficiary.user_id == user.id))
    ben = result.scalar_one_or_none()
    if not ben:
        raise HTTPException(status_code=404, detail="Beneficiary profile not found")
    return ben


@router.get("/status")
async def get_skillcraft_status(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get beneficiary's SkillCraft assessment status from the live API."""
    ben = await _get_beneficiary(user, db)
    status = await skillcraft_service.get_test_status(user.email)

    # Use live status from SkillCraft API as source of truth
    finished = status.get("finished", False)
    score = status.get("score") if finished else None

    # Clear stale DB score if the test isn't actually finished
    if not finished and ben.skillcraft_score is not None:
        ben.skillcraft_score = None
        ben.skillcraft_last_sync = None
        await db.commit()

    return {
        "skillcraft_user_id": ben.skillcraft_user_id,
        "finished": finished,
        "score": score,
        "last_sync": ben.skillcraft_last_sync.isoformat() if ben.skillcraft_last_sync else None,
        "external_status": status,
    }


@router.post("/start")
async def start_skillcraft(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register user on SkillCraft and return the test URL."""
    ben = await _get_beneficiary(user, db)

    if ben.skillcraft_user_id:
        return {
            "message": "Already registered for SkillCraft",
            "test_url": f"https://skillcraft.app/{skillcraft_service.pilot_group}",
        }

    result = await skillcraft_service.sign_in(user.email)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])

    ben.skillcraft_user_id = result["skillcraft_user_id"]
    await db.commit()

    return {
        "message": "SkillCraft test started",
        "skillcraft_user_id": result["skillcraft_user_id"],
        "test_url": f"https://skillcraft.app/{skillcraft_service.pilot_group}",
    }


@router.post("/sync")
async def sync_skillcraft(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Sync the beneficiary's SkillCraft score from the live API."""
    ben = await _get_beneficiary(user, db)

    result = await skillcraft_service.sync_score(user.email)
    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])

    if result.get("score") is not None:
        ben.skillcraft_score = result["score"]
        ben.skillcraft_last_sync = datetime.utcnow()

        # Also save skillcraft_user_id if not already set
        if not ben.skillcraft_user_id:
            sign_in = await skillcraft_service.sign_in(user.email)
            if "skillcraft_user_id" in sign_in:
                ben.skillcraft_user_id = sign_in["skillcraft_user_id"]

        await db.commit()
        return {"message": "SkillCraft score synced", "score": result["score"]}

    return {
        "message": "Assessment not yet completed",
        "finished": result.get("finished", False),
        "score": None,
    }
