"""Orchestration routes — trigger agents on jobs."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.api.schemas import OrchestrateRequest, OrchestrateResponse, SuccessResponse
from genie.config import settings
from genie.db.database import get_session
from genie.db.models import AgentLog, Job
from genie.tools.communication_tools import notify_assigned_subcontractor_after_orchestrate
from genie.tools.registry import DelegateBudget, ToolRegistry
from genie.tools.schedule_tools import ensure_schedule_for_assigned_job, get_schedule

router = APIRouter(prefix="/orchestrate", tags=["orchestrate"])
logger = logging.getLogger(__name__)


def _resolve_orchestrate_limits(body: OrchestrateRequest) -> tuple[int, int, int]:
    """Returns (pm_max_iterations, delegate_budget, specialist_max_iterations)."""
    pm_cap = settings.orchestrate_max_rounds_cap
    del_cap = settings.orchestrate_max_delegate_cap

    pm_iters = settings.max_agent_iterations if body.max_llm_rounds is None else body.max_llm_rounds
    pm_iters = max(1, min(pm_iters, pm_cap))

    delegates = settings.max_delegate_calls if body.max_specialist_agents is None else body.max_specialist_agents
    delegates = max(0, min(delegates, del_cap))

    spec_iters = (
        settings.max_specialist_iterations
        if body.max_rounds_per_specialist is None
        else body.max_rounds_per_specialist
    )
    spec_iters = max(1, min(spec_iters, pm_cap))

    return pm_iters, delegates, spec_iters


@router.post("", response_model=OrchestrateResponse)
async def orchestrate_job(body: OrchestrateRequest, db: AsyncSession = Depends(get_session)):
    # Verify job exists
    result = await db.execute(select(Job).where(Job.id == body.job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {body.job_id} not found")

    from genie.agents.project_manager import ProjectManagerAgent

    pm_iters, delegate_n, spec_iters = _resolve_orchestrate_limits(body)
    registry = ToolRegistry(
        db,
        delegate_budget=DelegateBudget(delegate_n),
        specialist_max_iterations=spec_iters,
    )
    agent = ProjectManagerAgent(db, registry)
    task = body.task or f"Manage this job end-to-end: '{job.title}' (job_id: {body.job_id})"
    if delegate_n == 0:
        task += (
            "\n\nOrchestration limits: Do not use delegate_to_agent — specialist delegations are disabled "
            "for this run. Use only your own tools (get_job, update_job_status, assign_subcontractor, "
            "get_schedule, create_schedule, update_schedule, find_available_slots)."
        )
    else:
        task += (
            f"\n\nOrchestration limits: You may use delegate_to_agent at most {delegate_n} time(s) on this run "
            f"(each call uses one slot). You have at most {pm_iters} tool-use rounds yourself — stay focused."
        )
    agent_result = await agent.run(task, {"job_id": body.job_id}, max_iterations=pm_iters)

    refreshed = await db.execute(select(Job).where(Job.id == body.job_id))
    job_after = refreshed.scalar_one_or_none()
    if job_after:
        filled = await ensure_schedule_for_assigned_job(db, body.job_id)
        if filled.get("created"):
            logger.info(
                "ensure_schedule_for_assigned_job created row for job %s (%s)",
                body.job_id,
                filled.get("via", "slots"),
            )

    # Always notify assigned subcontractor on both SMS + email when credentials allow (separate from LLM tool calls).
    refreshed = await db.execute(select(Job).where(Job.id == body.job_id))
    job_after = refreshed.scalar_one_or_none()
    if job_after and job_after.assigned_subcontractor_id:
        sched = await get_schedule(db, job_id=body.job_id)
        sched_line = None
        if sched.get("count"):
            first = sched["schedules"][0]
            sched_line = f"Next window: {first['scheduled_start']} → {first['scheduled_end']}"
        try:
            await notify_assigned_subcontractor_after_orchestrate(
                db,
                job_id=body.job_id,
                job_title=job_after.title,
                job_status=job_after.status,
                subcontractor_id=job_after.assigned_subcontractor_id,
                agent_summary=agent_result.summary,
                schedule_summary=sched_line,
            )
        except Exception:
            # Orchestration already succeeded; notification failures must not drop the API response.
            logger.exception("Post-orchestrate SMS/email notify failed for job %s", body.job_id)
    elif job_after:
        logger.info(
            "Post-orchestrate SMS/email skipped — no subcontractor assigned on job %s after run",
            body.job_id,
        )

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
