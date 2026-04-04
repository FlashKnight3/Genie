"""Subcontractor routes."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from genie.api.schemas import SubcontractorCreate, SuccessResponse
from genie.db.database import get_session
from genie.db.models import Subcontractor
from genie.tools.subcontractor_tools import get_subcontractor, search_subcontractors

router = APIRouter(prefix="/subcontractors", tags=["subcontractors"])


@router.get("", response_model=SuccessResponse)
async def list_subcontractors(
    skills: str | None = None,
    location: str | None = None,
    max_rate: float | None = None,
    min_rating: float | None = None,
    availability: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    skills_list = skills.split(",") if skills else None
    result = await search_subcontractors(
        db,
        skills=skills_list,
        location=location,
        max_hourly_rate=max_rate,
        min_rating=min_rating,
        availability_status=availability,
    )
    return SuccessResponse(success=True, message=f"{result['count']} subcontractors found.", data=result)


@router.post("", response_model=SuccessResponse, status_code=201)
async def create_subcontractor(body: SubcontractorCreate, db: AsyncSession = Depends(get_session)):
    sub = Subcontractor(
        id=str(uuid.uuid4()),
        name=body.name,
        email=body.email,
        phone=body.phone,
        skills=body.skills,
        hourly_rate=body.hourly_rate,
        location=body.location,
        rating=body.rating,
        availability_status="available",
        completed_jobs=0,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return SuccessResponse(
        success=True,
        message="Subcontractor added.",
        data={"id": sub.id, "name": sub.name},
    )


@router.get("/{subcontractor_id}", response_model=SuccessResponse)
async def get_subcontractor_endpoint(subcontractor_id: str, db: AsyncSession = Depends(get_session)):
    result = await get_subcontractor(db, subcontractor_id=subcontractor_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return SuccessResponse(success=True, message="Subcontractor retrieved.", data=result)
