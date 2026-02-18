from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from middleware.auth import verify_password, create_token, get_current_user

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
