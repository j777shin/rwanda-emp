from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from middleware.auth import require_admin
from services.ingazi import ingazi_service

router = APIRouter()


@router.post("/ingazi")
async def sync_ingazi(
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Bulk sync all beneficiaries' Ingazi completion rates from Strapi."""
    result = await ingazi_service.sync_all_progress(db)
    return result
