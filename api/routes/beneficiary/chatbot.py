from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from models.chatbot import ChatbotResult, ChatbotStage
from middleware.auth import require_beneficiary
from services.chatbot import (
    initialize_stages,
    get_current_stage,
    send_message,
    finish_stage,
    go_to_stage,
)
from services.report_generator import generate_pdf_report
from utils.helpers import TEST_ACCOUNT_EMAILS

router = APIRouter()


class MessageRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []


class FinishStageRequest(BaseModel):
    conversation_history: list[dict] = []


class GoToStageRequest(BaseModel):
    stage_number: int


async def _get_beneficiary(user: User, db: AsyncSession) -> Beneficiary:
    result = await db.execute(select(Beneficiary).where(Beneficiary.user_id == user.id))
    ben = result.scalar_one_or_none()
    if not ben:
        raise HTTPException(status_code=404, detail="Beneficiary profile not found")
    return ben


@router.get("/status")
async def get_chatbot_status(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    # Check if stages are initialized
    stages_result = await db.execute(
        select(ChatbotStage)
        .where(ChatbotStage.beneficiary_id == ben.id)
        .order_by(ChatbotStage.stage_number)
    )
    stages = stages_result.scalars().all()

    if not stages:
        # Initialize stages
        await initialize_stages(db, ben.id)
        stages_result = await db.execute(
            select(ChatbotStage)
            .where(ChatbotStage.beneficiary_id == ben.id)
            .order_by(ChatbotStage.stage_number)
        )
        stages = stages_result.scalars().all()

    # Get report if exists
    report_result = await db.execute(
        select(ChatbotResult).where(ChatbotResult.beneficiary_id == ben.id)
    )
    report = report_result.scalar_one_or_none()

    current = await get_current_stage(db, ben.id)

    return {
        "stages": [
            {
                "stage_number": s.stage_number,
                "stage_name": s.stage_name,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "summary": (s.stage_data or {}).get("summary") if s.stage_data else None,
            }
            for s in stages
        ],
        "current_stage": current.stage_number if current else None,
        "current_stage_name": current.stage_name if current else None,
        "completed": all(s.status == "completed" for s in stages),
        "report_ready": report is not None,
        "is_test_account": user.email in TEST_ACCOUNT_EMAILS,
        "business_development_goal": ben.business_development_text or "",
    }


@router.post("/message")
async def send_chatbot_message(
    body: MessageRequest,
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = await send_message(
        db, ben.id, body.message.strip(), body.conversation_history
    )
    return result


@router.post("/finish-stage")
async def finish_chatbot_stage(
    body: FinishStageRequest,
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)
    result = await finish_stage(db, ben.id, body.conversation_history)
    return result


@router.post("/go-to-stage")
async def go_to_chatbot_stage(
    body: GoToStageRequest,
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if user.email not in TEST_ACCOUNT_EMAILS:
        raise HTTPException(status_code=403, detail="Only test accounts can navigate between stages")

    ben = await _get_beneficiary(user, db)
    result = await go_to_stage(db, ben.id, body.stage_number)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/stages")
async def get_stages(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    stages_result = await db.execute(
        select(ChatbotStage)
        .where(ChatbotStage.beneficiary_id == ben.id)
        .order_by(ChatbotStage.stage_number)
    )
    stages = stages_result.scalars().all()

    return [
        {
            "stage_number": s.stage_number,
            "stage_name": s.stage_name,
            "status": s.status,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "summary": (s.stage_data or {}).get("summary") if s.stage_data else None,
        }
        for s in stages
    ]


@router.get("/report")
async def get_report(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    report_result = await db.execute(
        select(ChatbotResult).where(ChatbotResult.beneficiary_id == ben.id)
    )
    report = report_result.scalar_one_or_none()

    # Load stage summaries
    stages_result = await db.execute(
        select(ChatbotStage)
        .where(ChatbotStage.beneficiary_id == ben.id)
        .order_by(ChatbotStage.stage_number)
    )
    stages = stages_result.scalars().all()

    stage_summaries = [
        {
            "stage_number": s.stage_number,
            "stage_name": s.stage_name,
            "summary": (s.stage_data or {}).get("summary", "") if s.stage_data else "",
        }
        for s in stages
        if s.status == "completed"
    ]

    return {
        "beneficiary_name": ben.name,
        "business_development_goal": ben.business_development_text or "",
        "stage_summaries": stage_summaries,
        "entrepreneurship_score": float(report.entrepreneurship_score) if report and report.entrepreneurship_score else None,
        "readiness_level": report.readiness_level if report else None,
        "summary": report.summary if report else None,
        "recommendations": report.recommendations if report else None,
        "generated_at": report.created_at.isoformat() if report else None,
    }


@router.get("/report/pdf")
async def get_report_pdf(
    user: Annotated[User, Depends(require_beneficiary)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ben = await _get_beneficiary(user, db)

    report_result = await db.execute(
        select(ChatbotResult).where(ChatbotResult.beneficiary_id == ben.id)
    )
    report = report_result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=404, detail="Report not generated yet.")

    pdf_bytes = generate_pdf_report(
        name=ben.name,
        score=float(report.entrepreneurship_score) if report.entrepreneurship_score else 0,
        readiness_level=report.readiness_level or "Unknown",
        summary=report.summary or "",
        recommendations=report.recommendations or "",
    )

    return StreamingResponse(
        pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=report_{ben.name.replace(' ', '_')}.pdf"},
    )
