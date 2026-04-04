"""Job CRUD routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from genie.api.schemas import JobCreate, JobResponse, JobStatusUpdate, SuccessResponse
from genie.db.database import get_session
from genie.tools.job_tools import create_job, get_job, list_jobs, update_job_status

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=SuccessResponse, status_code=201)
async def create_job_endpoint(body: JobCreate, db: AsyncSession = Depends(get_session)):
    result = await create_job(
        db,
        title=body.title,
        description=body.description,
        location=body.location,
        budget=body.budget,
        required_skills=body.required_skills,
        start_date=body.start_date,
        end_date=body.end_date,
        priority=body.priority,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return SuccessResponse(success=True, message="Job created.", data=result)


@router.get("", response_model=SuccessResponse)
async def list_jobs_endpoint(
    status: str | None = None,
    priority: str | None = None,
    db: AsyncSession = Depends(get_session),
):
    result = await list_jobs(db, status=status, priority=priority)
    return SuccessResponse(success=True, message=f"{result['count']} jobs found.", data=result)


@router.get("/{job_id}", response_model=SuccessResponse)
async def get_job_endpoint(job_id: str, db: AsyncSession = Depends(get_session)):
    result = await get_job(db, job_id=job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return SuccessResponse(success=True, message="Job retrieved.", data=result)


@router.patch("/{job_id}/status", response_model=SuccessResponse)
async def update_job_status_endpoint(
    job_id: str,
    body: JobStatusUpdate,
    db: AsyncSession = Depends(get_session),
):
    result = await update_job_status(db, job_id=job_id, status=body.status, notes=body.notes)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return SuccessResponse(success=True, message="Job status updated.", data=result)
