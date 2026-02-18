from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import User
from models.beneficiary import Beneficiary
from middleware.auth import require_admin

router = APIRouter()


class AccountListItem(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    beneficiary_name: str | None = None
    created_at: str


class AccountListResponse(BaseModel):
    items: list[AccountListItem]
    total: int
    page: int
    page_size: int


class AccountUpdate(BaseModel):
    is_active: bool | None = None
    email: str | None = None


@router.get("", response_model=AccountListResponse)
async def list_accounts(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
):
    query = select(User, Beneficiary.name).outerjoin(Beneficiary, User.id == Beneficiary.user_id)
    count_query = select(func.count()).select_from(User)

    if search:
        search_filter = or_(User.email.ilike(f"%{search}%"), Beneficiary.name.ilike(f"%{search}%"))
        query = query.where(search_filter)
        count_query = count_query.outerjoin(Beneficiary, User.id == Beneficiary.user_id).where(search_filter)

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    if is_active is not None:
        query = query.where(User.is_active == is_active)
        count_query = count_query.where(User.is_active == is_active)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(User.created_at.desc())
    result = await db.execute(query)
    rows = result.all()

    items = []
    for user, ben_name in rows:
        items.append(AccountListItem(
            id=str(user.id),
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            beneficiary_name=ben_name,
            created_at=user.created_at.isoformat(),
        ))

    return AccountListResponse(items=items, total=total, page=page, page_size=page_size)


@router.put("/{user_id}")
async def update_account(
    user_id: UUID,
    body: AccountUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    return {"message": "Account updated successfully"}


@router.delete("/{user_id}")
async def deactivate_account(
    user_id: UUID,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    await db.commit()
    return {"message": "Account deactivated successfully"}
