from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from models.chatbot import ChatbotConversation, ChatbotResult
from middleware.auth import require_admin

router = APIRouter()


@router.get("/overview")
async def get_overview(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    total = (await db.execute(select(func.count()).select_from(Beneficiary))).scalar()
    selected = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(Beneficiary.selection_status == "selected")
    )).scalar()
    employment = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(Beneficiary.track == "employment")
    )).scalar()
    entrepreneurship = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(Beneficiary.track == "entrepreneurship")
    )).scalar()

    avg_skillcraft = (await db.execute(
        select(func.avg(Beneficiary.skillcraft_score)).where(Beneficiary.skillcraft_score.is_not(None))
    )).scalar()
    avg_pathways = (await db.execute(
        select(func.avg(Beneficiary.pathways_completion_rate)).where(Beneficiary.pathways_completion_rate.is_not(None))
    )).scalar()
    avg_eligibility = (await db.execute(
        select(func.avg(Beneficiary.eligibility_score)).where(Beneficiary.eligibility_score.is_not(None))
    )).scalar()

    chatbot_sessions = (await db.execute(
        select(func.count(func.distinct(ChatbotConversation.beneficiary_id)))
    )).scalar()

    return {
        "total_beneficiaries": total,
        "selected_count": selected,
        "employment_track": employment,
        "entrepreneurship_track": entrepreneurship,
        "avg_skillcraft_score": float(avg_skillcraft) if avg_skillcraft else None,
        "avg_pathways_rate": float(avg_pathways) if avg_pathways else None,
        "avg_eligibility_score": float(avg_eligibility) if avg_eligibility else None,
        "chatbot_sessions": chatbot_sessions,
    }


@router.get("/demographics")
async def get_demographics(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Gender distribution
    gender_result = await db.execute(
        select(Beneficiary.gender, func.count()).group_by(Beneficiary.gender)
    )
    gender = {row[0] or "unknown": row[1] for row in gender_result.all()}

    # Age distribution
    age_result = await db.execute(
        select(
            case(
                (Beneficiary.age.between(15, 19), "15-19"),
                (Beneficiary.age.between(20, 24), "20-24"),
                (Beneficiary.age.between(25, 29), "25-29"),
                (Beneficiary.age.between(30, 35), "30-35"),
            ).label("age_group"),
            func.count(),
        ).group_by("age_group")
    )
    age = {row[0]: row[1] for row in age_result.all() if row[0]}

    # Education distribution
    edu_result = await db.execute(
        select(Beneficiary.education_level, func.count())
        .where(Beneficiary.education_level.is_not(None))
        .group_by(Beneficiary.education_level)
    )
    education = {row[0]: row[1] for row in edu_result.all()}

    # District distribution
    district_result = await db.execute(
        select(Beneficiary.district, func.count())
        .where(Beneficiary.district.is_not(None))
        .group_by(Beneficiary.district)
        .order_by(func.count().desc())
    )
    districts = {row[0]: row[1] for row in district_result.all()}

    return {
        "gender": gender,
        "age_groups": age,
        "education": education,
        "districts": districts,
    }


@router.get("/engagement")
async def get_engagement(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # SkillCraft completion
    sc_total = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(Beneficiary.selection_status == "selected")
    )).scalar()
    sc_completed = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(Beneficiary.skillcraft_score.is_not(None))
    )).scalar()

    # Pathways enrollment
    pw_enrolled = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(Beneficiary.pathways_user_id.is_not(None))
    )).scalar()

    # Business dev submissions
    bd_submitted = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(Beneficiary.wants_entrepreneurship == True)
    )).scalar()

    # Chatbot engagement
    chatbot_users = (await db.execute(
        select(func.count(func.distinct(ChatbotConversation.beneficiary_id)))
    )).scalar()
    total_messages = (await db.execute(
        select(func.count()).select_from(ChatbotConversation)
    )).scalar()

    return {
        "skillcraft": {"total": sc_total, "completed": sc_completed},
        "pathways": {"enrolled": pw_enrolled},
        "business_development": {"submitted": bd_submitted},
        "chatbot": {"unique_users": chatbot_users, "total_messages": total_messages},
    }


@router.get("/socioeconomic")
async def get_socioeconomic(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Land ownership
    land_owners = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(Beneficiary.land_ownership == True)
    )).scalar()
    total = (await db.execute(select(func.count()).select_from(Beneficiary))).scalar()

    # Avg livestock
    avg_cattle = (await db.execute(select(func.avg(Beneficiary.num_cattle)))).scalar()
    avg_goats = (await db.execute(select(func.avg(Beneficiary.num_goats)))).scalar()

    # Housing
    earth_floor = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(Beneficiary.floor_earth_sand == True)
    )).scalar()
    has_lighting = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(Beneficiary.lighting == True)
    )).scalar()

    # Avg household size
    avg_hh = (await db.execute(select(func.avg(Beneficiary.household_size)))).scalar()

    return {
        "land_ownership_rate": land_owners / total if total else 0,
        "avg_cattle": float(avg_cattle) if avg_cattle else 0,
        "avg_goats": float(avg_goats) if avg_goats else 0,
        "earth_floor_rate": earth_floor / total if total else 0,
        "lighting_rate": has_lighting / total if total else 0,
        "avg_household_size": float(avg_hh) if avg_hh else 0,
        "total": total,
    }
