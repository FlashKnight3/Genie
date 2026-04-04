"""Schedule routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from genie.api.schemas import SuccessResponse
from genie.db.database import get_session
from genie.tools.schedule_tools import get_full_schedule, get_schedule

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("", response_model=SuccessResponse)
async def get_full_schedule_endpoint(db: AsyncSession = Depends(get_session)):
    result = await get_full_schedule(db)
    return SuccessResponse(success=True, message=f"{result['count']} schedule entries.", data=result)


@router.get("/{job_id}", response_model=SuccessResponse)
async def get_job_schedule(job_id: str, db: AsyncSession = Depends(get_session)):
    result = await get_schedule(db, job_id=job_id)
    return SuccessResponse(success=True, message=f"{result['count']} schedule entries for job.", data=result)
