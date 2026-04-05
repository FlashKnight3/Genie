"""Live agent activity stream — Server-Sent Events for real-time agent updates."""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.config import settings
from genie.db.database import get_session
from genie.db.models import Job
from genie.tools.registry import DelegateBudget, ToolRegistry

router = APIRouter(prefix="/orchestrate/stream", tags=["stream"])
logger = logging.getLogger(__name__)


@router.get("/{job_id}")
async def stream_orchestration(
    job_id: str,
    task: str | None = None,
    max_specialist_agents: int | None = None,
    max_llm_rounds: int | None = None,
    db: AsyncSession = Depends(get_session),
):
    """Stream live agent activity as Server-Sent Events while orchestrating a job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': f'Job {job_id} not found'})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    queue: asyncio.Queue = asyncio.Queue()

    async def event_callback(event: dict) -> None:
        await queue.put(event)

    # Resolve limits
    pm_cap = settings.orchestrate_max_rounds_cap
    del_cap = settings.orchestrate_max_delegate_cap

    pm_iters = settings.max_agent_iterations if max_llm_rounds is None else max_llm_rounds
    pm_iters = max(1, min(pm_iters, pm_cap))

    delegates = settings.max_delegate_calls if max_specialist_agents is None else max_specialist_agents
    delegates = max(0, min(delegates, del_cap))

    spec_iters = settings.max_specialist_iterations

    from genie.agents.project_manager import ProjectManagerAgent

    registry = ToolRegistry(
        db,
        delegate_budget=DelegateBudget(delegates),
        specialist_max_iterations=spec_iters,
    )
    # Attach the callback so delegate_to_agent can thread it through
    registry.event_callback = event_callback  # type: ignore[attr-defined]

    agent = ProjectManagerAgent(db, registry)
    agent_task_text = task or f"Manage this job end-to-end: '{job.title}' (job_id: {job_id})"

    # Run agent in background task
    agent_coro = agent.run(agent_task_text, context={"job_id": job_id}, max_iterations=pm_iters, event_callback=event_callback)
    background_task = asyncio.create_task(agent_coro)

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=60.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("type") == "done":
                        break
                except asyncio.TimeoutError:
                    # Send keepalive comment
                    yield ": keepalive\n\n"
                except asyncio.CancelledError:
                    break
        finally:
            if not background_task.done():
                background_task.cancel()

    async def run_and_signal():
        try:
            result = await background_task
            # Notify the post-orchestration hook
            from genie.tools.communication_tools import notify_assigned_subcontractor_after_orchestrate
            try:
                await notify_assigned_subcontractor_after_orchestrate(db, job_id, result.summary)
            except Exception:
                pass
            await queue.put({
                "type": "done",
                "success": True,
                "summary": result.summary[:300],
                "tool_calls_count": len(result.tool_calls_made),
            })
        except Exception as exc:
            await queue.put({"type": "done", "success": False, "error": str(exc)})

    asyncio.create_task(run_and_signal())

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
