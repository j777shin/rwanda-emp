from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from middleware.auth import require_admin
from services.pathways import pathways_service

router = APIRouter()


@router.post("/pathways")
async def sync_pathways(
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Bulk sync all beneficiaries' Pathways completion rates from Strapi."""
    result = await pathways_service.sync_all_progress(db)
    return result
