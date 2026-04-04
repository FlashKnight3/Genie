"""Authenticated user profile and onboarding."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.api.schemas import SuccessResponse, UserProfileOut, UserProfileUpdate
from genie.auth import get_current_user
from genie.db.database import get_session
from genie.db.models import UserProfile

router = APIRouter(prefix="/api/profile", tags=["profile"])


async def _get_or_create_profile(
    db: AsyncSession,
    user_id: str,
    email: str | None,
) -> UserProfile:
    result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    row = result.scalar_one_or_none()
    if row:
        if email and row.email != email:
            row.email = email
            await db.commit()
            await db.refresh(row)
        return row
    row = UserProfile(user_id=user_id, email=email)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


def _to_out(row: UserProfile) -> dict:
    return UserProfileOut(
        user_id=row.user_id,
        email=row.email,
        display_name=row.display_name,
        company_name=row.company_name,
        onboarding_completed=row.onboarding_completed,
    ).model_dump()


@router.get("", response_model=SuccessResponse)
async def get_profile(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    uid = user.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject")
    row = await _get_or_create_profile(db, uid, user.get("email"))
    return SuccessResponse(success=True, message="Profile loaded.", data=_to_out(row))


@router.patch("", response_model=SuccessResponse)
async def update_profile(
    body: UserProfileUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if body.model_dump(exclude_unset=True) == {}:
        raise HTTPException(status_code=400, detail="No fields to update")
    uid = user.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject")
    row = await _get_or_create_profile(db, uid, user.get("email"))
    if body.display_name is not None:
        row.display_name = body.display_name.strip() or None
    if body.company_name is not None:
        row.company_name = body.company_name.strip() or None
    if body.onboarding_completed is not None:
        row.onboarding_completed = body.onboarding_completed
    await db.commit()
    await db.refresh(row)
    return SuccessResponse(success=True, message="Profile updated.", data=_to_out(row))
