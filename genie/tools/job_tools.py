"""Tools for creating and managing jobs."""
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.db.models import Job, Subcontractor


TOOL_DEFINITIONS = [
    {
        "name": "create_job",
        "description": "Create a new job in the system.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "required_skills": {"type": "array", "items": {"type": "string"}},
                "location": {"type": "string"},
                "budget": {"type": "number"},
                "start_date": {"type": "string", "description": "ISO date string YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "ISO date string YYYY-MM-DD"},
                "priority": {"type": "string", "description": "low, medium, high, or critical"},
            },
            "required": ["title", "description", "location", "budget"],
        },
    },
    {
        "name": "get_job",
        "description": "Get full details of a job by ID, including assigned subcontractor info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "update_job_status",
        "description": "Update the status of a job. Valid statuses: pending, matching, assigned, in_progress, completed, at_risk, rescheduled, cancelled.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "status": {"type": "string"},
                "notes": {"type": "string", "description": "Optional notes about the status change"},
            },
            "required": ["job_id", "status"],
        },
    },
    {
        "name": "list_jobs",
        "description": "List jobs with optional status filter.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status (optional)"},
                "priority": {"type": "string", "description": "Filter by priority (optional)"},
            },
        },
    },
    {
        "name": "assign_subcontractor",
        "description": "Assign a subcontractor to a job and update job status to 'assigned'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "subcontractor_id": {"type": "string"},
            },
            "required": ["job_id", "subcontractor_id"],
        },
    },
    {
        "name": "get_job_timeline",
        "description": "Get a timeline summary for a job including schedule, risks, and messages.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
            },
            "required": ["job_id"],
        },
    },
]


def _job_to_dict(job: Job) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "required_skills": job.required_skills,
        "location": job.location,
        "status": job.status,
        "budget": job.budget,
        "start_date": job.start_date,
        "end_date": job.end_date,
        "priority": job.priority,
        "assigned_subcontractor_id": job.assigned_subcontractor_id,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


async def create_job(
    db: AsyncSession,
    title: str,
    description: str,
    location: str,
    budget: float,
    required_skills: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    priority: str = "medium",
) -> dict:
    job = Job(
        id=str(uuid.uuid4()),
        title=title,
        description=description,
        required_skills=required_skills or [],
        location=location,
        budget=budget,
        start_date=start_date,
        end_date=end_date,
        priority=priority,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return _job_to_dict(job)


async def get_job(db: AsyncSession, job_id: str) -> dict:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return {"error": f"Job {job_id} not found"}
    data = _job_to_dict(job)
    if job.assigned_subcontractor_id:
        sub_result = await db.execute(select(Subcontractor).where(Subcontractor.id == job.assigned_subcontractor_id))
        sub = sub_result.scalar_one_or_none()
        if sub:
            data["assigned_subcontractor"] = {"name": sub.name, "email": sub.email, "phone": sub.phone}
    return data


async def update_job_status(db: AsyncSession, job_id: str, status: str, notes: str | None = None) -> dict:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return {"error": f"Job {job_id} not found"}
    job.status = status
    job.updated_at = datetime.utcnow()
    await db.commit()
    return {"success": True, "job_id": job_id, "new_status": status, "notes": notes}


async def list_jobs(db: AsyncSession, status: str | None = None, priority: str | None = None) -> dict:
    stmt = select(Job)
    if status:
        stmt = stmt.where(Job.status == status)
    if priority:
        stmt = stmt.where(Job.priority == priority)
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return {"jobs": [_job_to_dict(j) for j in jobs], "count": len(jobs)}


async def assign_subcontractor(db: AsyncSession, job_id: str, subcontractor_id: str) -> dict:
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        return {"error": f"Job {job_id} not found"}

    sub_result = await db.execute(select(Subcontractor).where(Subcontractor.id == subcontractor_id))
    sub = sub_result.scalar_one_or_none()
    if not sub:
        return {"error": f"Subcontractor {subcontractor_id} not found"}

    job.assigned_subcontractor_id = subcontractor_id
    job.status = "assigned"
    job.updated_at = datetime.utcnow()
    sub.availability_status = "busy"
    await db.commit()
    return {
        "success": True,
        "job_id": job_id,
        "subcontractor_id": subcontractor_id,
        "subcontractor_name": sub.name,
        "job_status": "assigned",
    }


async def get_job_timeline(db: AsyncSession, job_id: str) -> dict:
    from genie.db.models import AgentLog, Message, Risk, Schedule

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return {"error": f"Job {job_id} not found"}

    sched_result = await db.execute(select(Schedule).where(Schedule.job_id == job_id))
    schedules = sched_result.scalars().all()

    risk_result = await db.execute(select(Risk).where(Risk.job_id == job_id))
    risks = risk_result.scalars().all()

    msg_result = await db.execute(select(Message).where(Message.job_id == job_id))
    messages = msg_result.scalars().all()

    log_result = await db.execute(select(AgentLog).where(AgentLog.job_id == job_id))
    logs = log_result.scalars().all()

    return {
        "job": _job_to_dict(job),
        "schedules": [
            {
                "id": s.id,
                "scheduled_start": s.scheduled_start,
                "scheduled_end": s.scheduled_end,
                "notes": s.notes,
            }
            for s in schedules
        ],
        "risks": [
            {
                "id": r.id,
                "risk_type": r.risk_type,
                "severity": r.severity,
                "description": r.description,
                "resolved": r.resolved_at is not None,
            }
            for r in risks
        ],
        "message_count": len(messages),
        "agent_actions": [{"agent": l.agent_name, "action": l.action, "timestamp": l.timestamp.isoformat()} for l in logs],
    }
