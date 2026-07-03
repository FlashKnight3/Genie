"""Delay detection — scans jobs for overdue tasks and pre-drafts follow-up messages."""
from datetime import date

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.api.schemas import SuccessResponse
from genie.config import settings
from genie.db.database import get_session
from genie.db.models import Job, Subcontractor

router = APIRouter(prefix="/delays", tags=["delays"])


@router.get("", response_model=SuccessResponse)
async def get_delays(db: AsyncSession = Depends(get_session)):
    """Return all overdue jobs with a pre-drafted follow-up SMS for each."""
    today = date.today().isoformat()

    result = await db.execute(
        select(Job).where(
            Job.status.in_(["in_progress", "assigned", "at_risk"]),
            Job.end_date < today,
            Job.assigned_subcontractor_id.isnot(None),
        )
    )
    overdue_jobs = result.scalars().all()

    alerts = []
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    for job in overdue_jobs:
        sub_result = await db.execute(
            select(Subcontractor).where(Subcontractor.id == job.assigned_subcontractor_id)
        )
        sub = sub_result.scalar_one_or_none()
        if not sub:
            continue

        days_overdue = (date.today() - date.fromisoformat(job.end_date)).days

        # Pre-draft a follow-up SMS via Claude
        draft_sms = await _draft_followup(client, job, sub, days_overdue)

        alerts.append({
            "job_id": job.id,
            "job_title": job.title,
            "status": job.status,
            "end_date": job.end_date,
            "days_overdue": days_overdue,
            "sub_id": sub.id,
            "sub_name": sub.name,
            "sub_phone": sub.phone,
            "sub_email": sub.email,
            "draft_sms": draft_sms,
        })

    return SuccessResponse(
        success=True,
        message=f"{len(alerts)} overdue job(s) detected.",
        data={"alerts": alerts},
    )


@router.post("/{job_id}/send", response_model=SuccessResponse)
async def send_delay_followup(job_id: str, db: AsyncSession = Depends(get_session)):
    """Approve and send the pre-drafted follow-up SMS for an overdue job."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.assigned_subcontractor_id:
        raise HTTPException(status_code=400, detail="No subcontractor assigned")

    sub_result = await db.execute(
        select(Subcontractor).where(Subcontractor.id == job.assigned_subcontractor_id)
    )
    sub = sub_result.scalar_one_or_none()

    days_overdue = 0
    if job.end_date:
        try:
            days_overdue = (date.today() - date.fromisoformat(job.end_date)).days
        except ValueError:
            pass

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    draft_sms = await _draft_followup(client, job, sub, days_overdue)

    from genie.tools.communication_tools import send_message

    send_result = await send_message(
        db,
        sub.id,
        "sms",
        f"Follow-up: {job.title}",
        draft_sms,
        job_id=job.id,
    )
    if not send_result.get("success"):
        raise HTTPException(status_code=400, detail=send_result.get("error", "Could not log message"))

    # Mark job as at_risk so it bubbles up in the UI
    if job.status != "at_risk":
        job.status = "at_risk"

    await db.commit()

    return SuccessResponse(
        success=True,
        message="Follow-up sent.",
        data={
            "message_id": send_result["message_id"],
            "recipient": sub.name,
            "sms_body": draft_sms,
            "delivery_status": send_result.get("delivery_status", "logged"),
        },
    )


async def _draft_followup(
    client: anthropic.AsyncAnthropic,
    job: Job,
    sub: Subcontractor,
    days_overdue: int,
) -> str:
    resp = await client.messages.create(
        model=settings.claude_model,
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": (
                f"Draft a professional but friendly follow-up SMS from a contractor to a subcontractor "
                f"whose job is overdue.\n\n"
                f"Sub name: {sub.name}\n"
                f"Job: {job.title}\n"
                f"Was due: {job.end_date} ({days_overdue} day(s) ago)\n\n"
                f"Keep it under 3 sentences. Firm but respectful. Ask for a status update and ETA. "
                f"Sound human, not corporate. Return only the SMS text."
            ),
        }],
    )
    return resp.content[0].text.strip()
