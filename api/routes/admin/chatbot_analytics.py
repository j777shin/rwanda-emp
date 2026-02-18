from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from models.chatbot import ChatbotConversation, ChatbotResult, ChatbotStage
from middleware.auth import require_admin

router = APIRouter()


@router.get("/analytics")
async def get_chatbot_analytics(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Total chatbot users
    total_users = (await db.execute(
        select(func.count(func.distinct(ChatbotConversation.beneficiary_id)))
    )).scalar()

    # Total messages
    total_messages = (await db.execute(
        select(func.count()).select_from(ChatbotConversation)
    )).scalar()

    # Stage completion rates
    stage_stats = []
    for stage_num in range(1, 6):
        total_at_stage = (await db.execute(
            select(func.count()).select_from(ChatbotStage)
            .where(ChatbotStage.stage_number == stage_num)
        )).scalar()
        completed = (await db.execute(
            select(func.count()).select_from(ChatbotStage)
            .where(ChatbotStage.stage_number == stage_num)
            .where(ChatbotStage.status == "completed")
        )).scalar()
        stage_stats.append({
            "stage": stage_num,
            "total": total_at_stage,
            "completed": completed,
            "rate": completed / total_at_stage if total_at_stage else 0,
        })

    # Reports generated
    reports = (await db.execute(
        select(func.count()).select_from(ChatbotResult)
    )).scalar()

    # Avg score
    avg_score = (await db.execute(
        select(func.avg(ChatbotResult.entrepreneurship_score))
        .where(ChatbotResult.entrepreneurship_score.is_not(None))
    )).scalar()

    # Readiness distribution
    readiness_result = await db.execute(
        select(ChatbotResult.readiness_level, func.count())
        .where(ChatbotResult.readiness_level.is_not(None))
        .group_by(ChatbotResult.readiness_level)
    )
    readiness = {row[0]: row[1] for row in readiness_result.all()}

    return {
        "total_users": total_users,
        "total_messages": total_messages,
        "stage_completion": stage_stats,
        "reports_generated": reports,
        "avg_score": float(avg_score) if avg_score else None,
        "readiness_distribution": readiness,
    }


@router.get("/conversations/{beneficiary_id}")
async def get_beneficiary_conversations(
    beneficiary_id: UUID,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Verify beneficiary exists
    ben_result = await db.execute(select(Beneficiary).where(Beneficiary.id == beneficiary_id))
    ben = ben_result.scalar_one_or_none()
    if not ben:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    # Get conversations
    conv_result = await db.execute(
        select(ChatbotConversation)
        .where(ChatbotConversation.beneficiary_id == beneficiary_id)
        .order_by(ChatbotConversation.created_at)
    )
    conversations = conv_result.scalars().all()

    # Get stages
    stages_result = await db.execute(
        select(ChatbotStage)
        .where(ChatbotStage.beneficiary_id == beneficiary_id)
        .order_by(ChatbotStage.stage_number)
    )
    stages = stages_result.scalars().all()

    # Get report
    report_result = await db.execute(
        select(ChatbotResult).where(ChatbotResult.beneficiary_id == beneficiary_id)
    )
    report = report_result.scalar_one_or_none()

    return {
        "beneficiary": {"id": str(ben.id), "name": ben.name},
        "conversations": [
            {
                "message": c.message,
                "is_user": c.is_user,
                "created_at": c.created_at.isoformat(),
            }
            for c in conversations
        ],
        "stages": [
            {
                "stage_number": s.stage_number,
                "stage_name": s.stage_name,
                "status": s.status,
            }
            for s in stages
        ],
        "report": {
            "score": float(report.entrepreneurship_score) if report and report.entrepreneurship_score else None,
            "readiness_level": report.readiness_level if report else None,
            "summary": report.summary if report else None,
        } if report else None,
    }
