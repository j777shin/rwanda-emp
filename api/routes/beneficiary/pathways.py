from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from middleware.auth import require_beneficiary
from services.pathways import pathways_service

router = APIRouter()


async def _get_beneficiary(user: User, db: AsyncSession) -> Beneficiary:
    result = await db.execute(select(Beneficiary).where(Beneficiary.user_id == user.id))
    ben = result.scalar_one_or_none()
    if not ben:
        raise HTTPException(status_code=404, detail="Beneficiary profile not found")
    return ben


@router.get("/status")
async def get_pathways_status(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)
    progress = await pathways_service.get_progress(user.email)

    return {
        "pathways_user_id": ben.pathways_user_id,
        "completion_rate": float(ben.pathways_completion_rate) if ben.pathways_completion_rate else progress.get("completion_rate"),
        "last_sync": ben.pathways_last_sync.isoformat() if ben.pathways_last_sync else None,
        "external_progress": progress,
        "course_progress": ben.pathways_course_progress or progress.get("course_progress", {}),
    }


@router.post("/enroll")
async def enroll_pathways(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    if ben.pathways_user_id:
        # Already enrolled - just return current progress
        progress = await pathways_service.get_progress(user.email)
        return {
            "message": "Already enrolled in Pathways",
            "platform_url": progress.get("url"),
        }

    result = await pathways_service.enroll(user.email)
    if result.get("pathways_user_id"):
        ben.pathways_user_id = result["pathways_user_id"]
        await db.commit()

    return {"message": "Enrolled in Pathways", **result}


@router.post("/sync")
async def sync_pathways(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)
    progress = await pathways_service.get_progress(user.email)

    ben.pathways_completion_rate = progress.get("completion_rate", 0)
    ben.pathways_course_progress = progress.get("course_progress", {})
    ben.pathways_last_sync = datetime.utcnow()
    await db.commit()

    return {
        "message": "Pathways progress synced",
        "completion_rate": progress.get("completion_rate", 0),
        "course_progress": progress.get("course_progress", {}),
    }
