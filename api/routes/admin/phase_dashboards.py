from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from models.chatbot import ChatbotResult, ChatbotStage
from middleware.auth import require_admin
from utils.helpers import test_account_user_ids_subquery

router = APIRouter()


@router.get("/phase1/dashboard")
async def get_phase1_dashboard(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())

    selected = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.selection_status == "selected")
    )).scalar()

    # SkillCraft stats
    sc_completed = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(exc, Beneficiary.selection_status == "selected")
        .where(Beneficiary.skillcraft_score.is_not(None))
    )).scalar()
    avg_sc = (await db.execute(
        select(func.avg(Beneficiary.skillcraft_score))
        .where(exc, Beneficiary.skillcraft_score.is_not(None))
    )).scalar()

    # Pathways stats
    pw_enrolled = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(exc, Beneficiary.selection_status == "selected")
        .where(Beneficiary.pathways_user_id.is_not(None))
    )).scalar()
    avg_pw = (await db.execute(
        select(func.avg(Beneficiary.pathways_completion_rate))
        .where(exc, Beneficiary.pathways_completion_rate.is_not(None))
    )).scalar()

    # Business dev
    bd_interest = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(exc, Beneficiary.selection_status == "selected")
        .where(Beneficiary.wants_entrepreneurship == True)
    )).scalar()

    # Avg attendance
    avg_attendance = (await db.execute(
        select(func.avg(Beneficiary.offline_attendance))
        .where(exc, Beneficiary.selection_status == "selected")
    )).scalar()

    return {
        "total_selected": selected,
        "skillcraft": {
            "completed": sc_completed,
            "completion_rate": sc_completed / selected if selected else 0,
            "avg_score": float(avg_sc) if avg_sc else None,
        },
        "pathways": {
            "enrolled": pw_enrolled,
            "enrollment_rate": pw_enrolled / selected if selected else 0,
            "avg_completion": float(avg_pw) if avg_pw else None,
        },
        "business_development": {
            "interested": bd_interest,
            "interest_rate": bd_interest / selected if selected else 0,
        },
        "avg_offline_attendance": float(avg_attendance) if avg_attendance else 0,
    }


@router.get("/phase2/dashboard")
async def get_phase2_dashboard(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())

    employment = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.track == "employment")
    )).scalar()
    entrepreneurship = (await db.execute(
        select(func.count()).select_from(Beneficiary).where(exc, Beneficiary.track == "entrepreneurship")
    )).scalar()

    # Employment outcomes
    hired = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(exc, Beneficiary.track == "employment")
        .where(Beneficiary.hired == True)
    )).scalar()
    self_emp = (await db.execute(
        select(func.count()).select_from(Beneficiary)
        .where(exc, Beneficiary.self_employed == True)
    )).scalar()

    # Entrepreneurship - reports generated
    reports = (await db.execute(
        select(func.count()).select_from(ChatbotResult)
    )).scalar()
    avg_ent_score = (await db.execute(
        select(func.avg(ChatbotResult.entrepreneurship_score))
        .where(ChatbotResult.entrepreneurship_score.is_not(None))
    )).scalar()

    return {
        "employment_track": {
            "total": employment,
            "hired": hired,
            "hire_rate": hired / employment if employment else 0,
        },
        "entrepreneurship_track": {
            "total": entrepreneurship,
            "reports_completed": reports,
            "avg_score": float(avg_ent_score) if avg_ent_score else None,
            "self_employed": self_emp,
        },
    }


@router.get("/progress/employment")
async def get_employment_progress(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())
    result = await db.execute(
        select(Beneficiary, User.email)
        .join(User, Beneficiary.user_id == User.id)
        .where(exc, Beneficiary.track == "employment")
        .order_by(Beneficiary.pathways_completion_rate.desc().nullslast())
        .limit(100)
    )
    rows = result.all()

    return [
        {
            "id": str(ben.id),
            "name": ben.name,
            "email": email,
            "pathways_completion_rate": float(ben.pathways_completion_rate) if ben.pathways_completion_rate else None,
            "hired": ben.hired,
            "self_employed": ben.self_employed,
            "offline_attendance": ben.offline_attendance,
        }
        for ben, email in rows
    ]


@router.get("/progress/entrepreneurship")
async def get_entrepreneurship_progress(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    exc = Beneficiary.user_id.not_in(test_account_user_ids_subquery())
    result = await db.execute(
        select(Beneficiary, User.email, ChatbotResult)
        .join(User, Beneficiary.user_id == User.id)
        .outerjoin(ChatbotResult, Beneficiary.id == ChatbotResult.beneficiary_id)
        .where(exc, Beneficiary.track == "entrepreneurship")
        .limit(100)
    )
    rows = result.all()

    items = []
    for ben, email, report in rows:
        # Get stage progress
        stages_result = await db.execute(
            select(func.count()).select_from(ChatbotStage)
            .where(ChatbotStage.beneficiary_id == ben.id)
            .where(ChatbotStage.status == "completed")
        )
        completed_stages = stages_result.scalar()

        items.append({
            "id": str(ben.id),
            "name": ben.name,
            "email": email,
            "stages_completed": completed_stages,
            "total_stages": 5,
            "report_ready": report is not None,
            "entrepreneurship_score": float(report.entrepreneurship_score) if report and report.entrepreneurship_score else None,
            "readiness_level": report.readiness_level if report else None,
        })

    return items
