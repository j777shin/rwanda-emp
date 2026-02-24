from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from models.chatbot import ChatbotConversation, ChatbotResult, ChatbotStage
from models.survey import SurveyResponse
from models.activity_log import ActivityLog
from middleware.auth import require_admin
from utils.helpers import test_account_user_ids_subquery

router = APIRouter()


class BeneficiaryListItem(BaseModel):
    id: str
    name: str
    age: int
    gender: str | None
    email: str | None
    contact: str | None
    district: str | None
    education_level: str | None
    selection_status: str
    track: str | None
    eligibility_score: float | None
    skillcraft_score: float | None
    pathways_completion_rate: float | None
    pathways_course_progress: dict | None = None
    offline_attendance: int
    hired: bool
    wants_entrepreneurship: bool
    business_development_text: str | None


class BeneficiaryListResponse(BaseModel):
    items: list[BeneficiaryListItem]
    total: int
    page: int
    page_size: int


class BeneficiaryUpdate(BaseModel):
    name: str | None = None
    age: int | None = None
    gender: str | None = None
    contact: str | None = None
    district: str | None = None
    education_level: str | None = None
    selection_status: str | None = None
    track: str | None = None
    offline_attendance: int | None = None
    email: str | None = None


@router.get("", response_model=BeneficiaryListResponse)
async def list_beneficiaries(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50000),
    search: str | None = None,
    selection_status: str | None = None,
    track: str | None = None,
    district: str | None = None,
    sort_by: str | None = Query(None, pattern="^(eligibility_score|created_at|name|age)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    query = select(Beneficiary, User.email).join(User, Beneficiary.user_id == User.id)
    count_query = select(func.count()).select_from(Beneficiary)

    # Exclude test accounts from admin portal
    exclude_test = Beneficiary.user_id.not_in(test_account_user_ids_subquery())
    query = query.where(exclude_test)
    count_query = count_query.where(exclude_test)

    if search:
        search_filter = or_(
            Beneficiary.name.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.join(User, Beneficiary.user_id == User.id).where(search_filter)

    if selection_status:
        query = query.where(Beneficiary.selection_status == selection_status)
        count_query = count_query.where(Beneficiary.selection_status == selection_status)

    if track:
        query = query.where(Beneficiary.track == track)
        count_query = count_query.where(Beneficiary.track == track)

    if district:
        query = query.where(Beneficiary.district == district)
        count_query = count_query.where(Beneficiary.district == district)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Sorting
    sort_column_map = {
        "eligibility_score": Beneficiary.eligibility_score,
        "created_at": Beneficiary.created_at,
        "name": Beneficiary.name,
        "age": Beneficiary.age,
    }
    sort_col = sort_column_map.get(sort_by, Beneficiary.created_at)
    order = sort_col.asc() if sort_order == "asc" else sort_col.desc()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(order)
    result = await db.execute(query)
    rows = result.all()

    items = []
    for ben, email in rows:
        items.append(BeneficiaryListItem(
            id=str(ben.id),
            name=ben.name,
            age=ben.age,
            gender=ben.gender,
            email=email,
            contact=ben.contact,
            district=ben.district,
            education_level=ben.education_level,
            selection_status=ben.selection_status,
            track=ben.track,
            eligibility_score=float(ben.eligibility_score) if ben.eligibility_score else None,
            skillcraft_score=float(ben.skillcraft_score) if ben.skillcraft_score else None,
            pathways_completion_rate=float(ben.pathways_completion_rate) if ben.pathways_completion_rate else None,
            pathways_course_progress=ben.pathways_course_progress,
            offline_attendance=ben.offline_attendance,
            hired=ben.hired,
            wants_entrepreneurship=ben.wants_entrepreneurship,
            business_development_text=ben.business_development_text,
        ))

    return BeneficiaryListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{beneficiary_id}")
async def get_beneficiary(
    beneficiary_id: UUID,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Beneficiary, User.email)
        .join(User, Beneficiary.user_id == User.id)
        .where(Beneficiary.id == beneficiary_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    ben, email = row
    return {
        "id": str(ben.id),
        "user_id": str(ben.user_id),
        "email": email,
        "name": ben.name,
        "age": ben.age,
        "gender": ben.gender,
        "contact": ben.contact,
        "district": ben.district,
        "education_level": ben.education_level,
        "marriage_status": ben.marriage_status,
        "disability": ben.disability,
        "occupation": ben.occupation,
        "informal_working": ben.informal_working,
        "num_goats": ben.num_goats,
        "num_sheep": ben.num_sheep,
        "num_pigs": ben.num_pigs,
        "num_cattle": ben.num_cattle,
        "land_ownership": ben.land_ownership,
        "land_size": float(ben.land_size) if ben.land_size else 0,
        "num_radio": ben.num_radio,
        "num_phone": ben.num_phone,
        "num_tv": ben.num_tv,
        "cooking_firewood": ben.cooking_firewood,
        "cooking_gas": ben.cooking_gas,
        "cooking_charcoal": ben.cooking_charcoal,
        "floor_earth_sand": ben.floor_earth_sand,
        "floor_tiles": ben.floor_tiles,
        "lighting": ben.lighting,
        "household_size": ben.household_size,
        "children_under_18": ben.children_under_18,
        "hh_head_university": ben.hh_head_university,
        "hh_head_primary": ben.hh_head_primary,
        "hh_head_secondary": ben.hh_head_secondary,
        "hh_head_married": ben.hh_head_married,
        "hh_head_widow": ben.hh_head_widow,
        "hh_head_divorced": ben.hh_head_divorced,
        "hh_head_female": ben.hh_head_female,
        "selection_status": ben.selection_status,
        "track": ben.track,
        "eligibility_score": float(ben.eligibility_score) if ben.eligibility_score else None,
        "skillcraft_score": float(ben.skillcraft_score) if ben.skillcraft_score else None,
        "pathways_completion_rate": float(ben.pathways_completion_rate) if ben.pathways_completion_rate else None,
        "pathways_course_progress": ben.pathways_course_progress,
        "offline_attendance": ben.offline_attendance,
        "self_employed": ben.self_employed,
        "hired": ben.hired,
        "wants_entrepreneurship": ben.wants_entrepreneurship,
        "business_development_text": ben.business_development_text,
    }


@router.put("/{beneficiary_id}")
async def update_beneficiary(
    beneficiary_id: UUID,
    body: BeneficiaryUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Beneficiary).where(Beneficiary.id == beneficiary_id))
    ben = result.scalar_one_or_none()
    if not ben:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    update_data = body.model_dump(exclude_unset=True)

    # Handle email separately — it lives on the User model, not Beneficiary
    new_email = update_data.pop("email", None)
    if new_email is not None:
        user_result = await db.execute(select(User).where(User.id == ben.user_id))
        user = user_result.scalar_one_or_none()
        if user:
            user.email = new_email

    for key, value in update_data.items():
        setattr(ben, key, value)

    await db.commit()
    return {"message": "Beneficiary updated successfully"}


@router.delete("/{beneficiary_id}")
async def delete_beneficiary(
    beneficiary_id: UUID,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Permanently delete a beneficiary and their user account."""
    result = await db.execute(select(Beneficiary).where(Beneficiary.id == beneficiary_id))
    ben = result.scalar_one_or_none()
    if not ben:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    # Delete related data
    await db.execute(delete(ChatbotConversation).where(ChatbotConversation.beneficiary_id == ben.id))
    await db.execute(delete(ChatbotStage).where(ChatbotStage.beneficiary_id == ben.id))
    await db.execute(delete(ChatbotResult).where(ChatbotResult.beneficiary_id == ben.id))
    await db.execute(delete(SurveyResponse).where(SurveyResponse.beneficiary_id == ben.id))

    user_id = ben.user_id
    await db.delete(ben)
    await db.execute(delete(ActivityLog).where(ActivityLog.user_id == user_id))
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()
    return {"message": "Account permanently deleted"}
