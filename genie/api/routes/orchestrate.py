"""Orchestration routes — trigger agents on jobs."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.api.schemas import OrchestrateRequest, OrchestrateResponse, SuccessResponse
from genie.db.database import get_session
from genie.db.models import AgentLog, Job
from genie.tools.registry import ToolRegistry

router = APIRouter(prefix="/orchestrate", tags=["orchestrate"])


@router.post("", response_model=OrchestrateResponse)
async def orchestrate_job(body: OrchestrateRequest, db: AsyncSession = Depends(get_session)):
    # Verify job exists
    result = await db.execute(select(Job).where(Job.id == body.job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {body.job_id} not found")

    from genie.agents.project_manager import ProjectManagerAgent

    registry = ToolRegistry(db)
    agent = ProjectManagerAgent(db, registry)
    task = body.task or f"Manage this job end-to-end: '{job.title}' (job_id: {body.job_id})"
    agent_result = await agent.run(task, {"job_id": body.job_id})

    return OrchestrateResponse(
        job_id=body.job_id,
        agent="project_manager",
        success=agent_result.success,
        summary=agent_result.summary,
        tool_calls_count=len(agent_result.tool_calls_made),
    )


@router.get("/logs", response_model=SuccessResponse)
async def get_agent_logs(limit: int = 50, db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(AgentLog).order_by(AgentLog.timestamp.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return SuccessResponse(
        success=True,
        message=f"{len(logs)} agent log entries.",
        data={
            "logs": [
                {
                    "id": l.id,
                    "agent_name": l.agent_name,
                    "job_id": l.job_id,
                    "action": l.action,
                    "tool_calls": l.tool_calls,
                    "timestamp": l.timestamp.isoformat() if l.timestamp else None,
                }
                for l in logs
            ]
        },
    )


@router.get("/risks", response_model=SuccessResponse)
async def get_all_risks(db: AsyncSession = Depends(get_session)):
    from genie.db.models import Risk

    result = await db.execute(select(Risk).order_by(Risk.triggered_at.desc()))
    risks = result.scalars().all()
    return SuccessResponse(
        success=True,
        message=f"{len(risks)} risk records.",
        data={
            "risks": [
                {
                    "id": r.id,
                    "job_id": r.job_id,
                    "risk_type": r.risk_type,
                    "severity": r.severity,
                    "description": r.description,
                    "resolved": r.resolved_at is not None,
                    "triggered_at": r.triggered_at.isoformat() if r.triggered_at else None,
                }
                for r in risks
            ]
        },
    )


@router.get("/messages/{job_id}", response_model=SuccessResponse)
async def get_job_messages(job_id: str, db: AsyncSession = Depends(get_session)):
    from genie.db.models import Message

    result = await db.execute(select(Message).where(Message.job_id == job_id).order_by(Message.sent_at))
    messages = result.scalars().all()
    return SuccessResponse(
        success=True,
        message=f"{len(messages)} messages for job.",
        data={
            "messages": [
                {
                    "id": m.id,
                    "direction": m.direction,
                    "channel": m.channel,
                    "subject": m.subject,
                    "body": m.body,
                    "sent_at": m.sent_at.isoformat() if m.sent_at else None,
                    "status": m.status,
                }
                for m in messages
            ]
        },
    )
