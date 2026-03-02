from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from middleware.auth import require_beneficiary

router = APIRouter()


class BusinessDevSubmission(BaseModel):
    wants_entrepreneurship: bool
    business_development_text: str = ""


async def _get_beneficiary(user: User, db: AsyncSession) -> Beneficiary:
    result = await db.execute(select(Beneficiary).where(Beneficiary.user_id == user.id))
    ben = result.scalar_one_or_none()
    if not ben:
        raise HTTPException(status_code=404, detail="Beneficiary profile not found")
    return ben


@router.get("")
async def get_business_dev(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)
    return {
        "wants_entrepreneurship": ben.wants_entrepreneurship,
        "business_development_text": ben.business_development_text,
    }


@router.post("")
async def submit_business_dev(
    body: BusinessDevSubmission,
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    # Validate word count
    if body.business_development_text:
        words = body.business_development_text.strip().split()
        if len(words) > 200:
            raise HTTPException(status_code=400, detail="Business development text exceeds 200 word limit")

    ben.wants_entrepreneurship = body.wants_entrepreneurship
    if body.wants_entrepreneurship:
        ben.business_development_text = body.business_development_text
    await db.commit()

    return {"message": "Business development goal submitted successfully"}
