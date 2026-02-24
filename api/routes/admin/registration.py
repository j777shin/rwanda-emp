from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from middleware.auth import require_admin, hash_password
from services.csv_processor import parse_csv

router = APIRouter()


class ManualRegistration(BaseModel):
    email: str
    name: str
    age: int
    gender: str
    contact: str | None = None
    district: str | None = None
    education_level: str | None = None
    marriage_status: bool = False
    disability: bool = False
    occupation: bool = False
    informal_working: bool = False
    num_goats: int = 0
    num_sheep: int = 0
    num_pigs: int = 0
    num_cattle: int = 0
    land_ownership: bool = False
    land_size: float = 0
    num_radio: int = 0
    num_phone: int = 0
    num_tv: int = 0
    cooking_firewood: bool = False
    cooking_gas: bool = False
    cooking_charcoal: bool = False
    floor_earth_sand: bool = False
    floor_tiles: bool = False
    lighting: bool = False
    children_under_18: int = 0
    household_size: int = 0
    hh_head_university: bool = False
    hh_head_primary: bool = False
    hh_head_secondary: bool = False
    hh_head_married: bool = False
    hh_head_widow: bool = False
    hh_head_divorced: bool = False
    hh_head_female: bool = False


@router.post("/csv")
async def upload_csv(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")

    content = await file.read()
    text = content.decode("utf-8")
    records, errors = parse_csv(text)

    if errors and not records:
        return {"success": False, "errors": errors, "created": 0}

    created = 0
    skipped_emails = []

    for rec in records:
        email = rec.pop("email")

        # Check if user already exists
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            skipped_emails.append(email)
            continue

        # Create user with default password (user should change on first login)
        user = User(
            email=email,
            password_hash=hash_password("changeme123"),
            role="beneficiary",
        )
        db.add(user)
        await db.flush()

        # Create beneficiary
        ben = Beneficiary(user_id=user.id, is_manual_entry=True, **rec)
        db.add(ben)
        created += 1

    await db.commit()

    return {
        "success": True,
        "created": created,
        "skipped": len(skipped_emails),
        "skipped_emails": skipped_emails[:20],  # limit output
        "errors": errors,
        "total_in_csv": len(records) + len(errors),
    }


@router.post("/manual")
async def register_manual(
    body: ManualRegistration,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email,
        password_hash=hash_password("changeme123"),
        role="beneficiary",
    )
    db.add(user)
    await db.flush()

    ben_data = body.model_dump(exclude={"email"})
    ben = Beneficiary(user_id=user.id, is_manual_entry=True, **ben_data)
    db.add(ben)
    await db.commit()

    return {"message": "Candidate registered successfully", "user_id": str(user.id), "beneficiary_id": str(ben.id)}
