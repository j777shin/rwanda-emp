from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from models.chatbot import ChatbotConversation, ChatbotResult, ChatbotStage
from models.survey import SurveyResponse
from models.activity_log import ActivityLog
from middleware.auth import verify_password, create_token, get_current_user
from utils.helpers import TEST_ACCOUNT_EMAILS

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict


class UserProfile(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    beneficiary: dict | None = None


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    token = create_token(str(user.id), user.role)

    user_data = {"id": str(user.id), "email": user.email, "role": user.role}

    # If beneficiary, include beneficiary data
    if user.role == "beneficiary":
        ben_result = await db.execute(
            select(Beneficiary).where(Beneficiary.user_id == user.id)
        )
        ben = ben_result.scalar_one_or_none()
        if ben:
            user_data["beneficiary"] = {
                "id": str(ben.id),
                "name": ben.name,
                "track": ben.track,
                "selection_status": ben.selection_status,
                "skillcraft_score": float(ben.skillcraft_score) if ben.skillcraft_score else None,
                "pathways_completion_rate": float(ben.pathways_completion_rate) if ben.pathways_completion_rate else None,
                "wants_entrepreneurship": ben.wants_entrepreneurship,
            }

    return LoginResponse(token=token, user=user_data)


@router.get("/me")
async def get_me(user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_db)]):
    user_data = {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
    }

    if user.role == "beneficiary":
        ben_result = await db.execute(
            select(Beneficiary).where(Beneficiary.user_id == user.id)
        )
        ben = ben_result.scalar_one_or_none()
        if ben:
            user_data["beneficiary"] = {
                "id": str(ben.id),
                "name": ben.name,
                "age": ben.age,
                "gender": ben.gender,
                "contact": ben.contact,
                "district": ben.district,
                "education_level": ben.education_level,
                "track": ben.track,
                "selection_status": ben.selection_status,
                "skillcraft_score": float(ben.skillcraft_score) if ben.skillcraft_score else None,
                "pathways_completion_rate": float(ben.pathways_completion_rate) if ben.pathways_completion_rate else None,
                "eligibility_score": float(ben.eligibility_score) if ben.eligibility_score else None,
                "wants_entrepreneurship": ben.wants_entrepreneurship,
                "business_development_text": ben.business_development_text,
                "offline_attendance": ben.offline_attendance,
                "self_employed": ben.self_employed,
                "hired": ben.hired,
            }

    return user_data


@router.post("/logout")
async def logout(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Logout endpoint.
    Admin test account: deletes all manually registered beneficiaries (is_manual_entry=True).
    Beneficiary test account: resets progress data to initial state."""
    if user.email not in TEST_ACCOUNT_EMAILS:
        return {"success": True}

    # Admin — delete all manually registered users
    if user.role == "admin":
        # Find all manually registered beneficiaries
        manual_bens = await db.execute(
            select(Beneficiary).where(Beneficiary.is_manual_entry == True)
        )
        manual_bens = manual_bens.scalars().all()

        for ben in manual_bens:
            user_id = ben.user_id
            # Delete related data
            await db.execute(delete(ChatbotConversation).where(ChatbotConversation.beneficiary_id == ben.id))
            await db.execute(delete(ChatbotStage).where(ChatbotStage.beneficiary_id == ben.id))
            await db.execute(delete(ChatbotResult).where(ChatbotResult.beneficiary_id == ben.id))
            await db.execute(delete(SurveyResponse).where(SurveyResponse.beneficiary_id == ben.id))
            await db.execute(delete(ActivityLog).where(ActivityLog.user_id == user_id))
            await db.execute(delete(Beneficiary).where(Beneficiary.id == ben.id))
            await db.execute(delete(User).where(User.id == user_id))

        await db.commit()
        return {"success": True}

    # --- Beneficiary test account cleanup: reset progress data ---
    ben_result = await db.execute(
        select(Beneficiary).where(Beneficiary.user_id == user.id)
    )
    ben = ben_result.scalar_one_or_none()
    if not ben:
        return {"success": True}

    # Delete chatbot data (conversations, stages, results)
    await db.execute(delete(ChatbotConversation).where(ChatbotConversation.beneficiary_id == ben.id))
    await db.execute(delete(ChatbotStage).where(ChatbotStage.beneficiary_id == ben.id))
    await db.execute(delete(ChatbotResult).where(ChatbotResult.beneficiary_id == ben.id))

    # Delete survey responses
    await db.execute(delete(SurveyResponse).where(SurveyResponse.beneficiary_id == ben.id))

    # Reset beneficiary fields to initial state
    ben.skillcraft_score = None
    ben.pathways_completion_rate = None
    ben.eligibility_score = None
    ben.self_employed = False
    ben.hired = False
    ben.hired_company_name = None
    ben.self_employed_description = None

    await db.commit()
    return {"success": True}
