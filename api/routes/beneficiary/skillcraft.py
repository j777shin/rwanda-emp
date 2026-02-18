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
    ben = await _get_beneficiary(user, db)
    status = await skillcraft_service.get_test_status(ben.skillcraft_user_id)

    return {
        "skillcraft_user_id": ben.skillcraft_user_id,
        "score": float(ben.skillcraft_score) if ben.skillcraft_score else None,
        "last_sync": ben.skillcraft_last_sync.isoformat() if ben.skillcraft_last_sync else None,
        "external_status": status,
    }


@router.post("/start")
async def start_skillcraft(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    if ben.skillcraft_user_id:
        return {
            "message": "Already registered for SkillCraft",
            "test_url": f"https://skillcraft.example.com/test/{ben.skillcraft_user_id}",
        }

    result = await skillcraft_service.start_test(str(ben.id))
    ben.skillcraft_user_id = result["skillcraft_user_id"]
    await db.commit()

    return {"message": "SkillCraft test started", **result}


@router.post("/sync")
async def sync_skillcraft(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    if not ben.skillcraft_user_id:
        raise HTTPException(status_code=400, detail="Not registered for SkillCraft yet")

    result = await skillcraft_service.sync_score(ben.skillcraft_user_id)
    ben.skillcraft_score = result["score"]
    ben.skillcraft_last_sync = datetime.utcnow()
    await db.commit()

    return {"message": "SkillCraft score synced", "score": result["score"]}
