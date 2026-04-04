"""Lead capture and AI auto-response."""
import uuid

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.api.schemas import SuccessResponse
from genie.config import settings
from genie.db.database import get_session
from genie.db.models import Lead

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadIn(BaseModel):
    name: str
    email: str
    phone: str | None = None
    message: str


@router.post("", response_model=SuccessResponse)
async def submit_lead(body: LeadIn, db: AsyncSession = Depends(get_session)):
    """Submit a new lead. Triggers AI auto-response + summary generation."""
    lead = Lead(
        id=str(uuid.uuid4()),
        name=body.name,
        email=body.email,
        phone=body.phone,
        message=body.message,
        status="new",
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)

    # Run AI auto-response + summary in the background of this request
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    auto_reply, ai_summary = await _process_lead(client, body.name, body.email, body.message)

    # Update lead with AI summary
    lead.ai_summary = ai_summary
    lead.status = "responded"
    lead.auto_reply_sent = True
    await db.commit()

    # Send the auto-reply email if Resend is configured
    delivery_status = "logged"
    if settings.resend_api_key:
        from genie.tools.communication_tools import _send_resend_email
        try:
            await _send_resend_email(
                to_email=body.email,
                subject="Thanks for reaching out — we'll be in touch shortly",
                body=auto_reply,
            )
            delivery_status = "sent"
        except Exception as exc:
            delivery_status = f"email_failed: {exc}"

    return SuccessResponse(
        success=True,
        message="Lead captured and auto-response sent.",
        data={
            "lead_id": lead.id,
            "auto_reply": auto_reply,
            "ai_summary": ai_summary,
            "delivery_status": delivery_status,
        },
    )


@router.get("", response_model=SuccessResponse)
async def list_leads(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Lead).order_by(Lead.received_at.desc()))
    leads = result.scalars().all()
    return SuccessResponse(
        success=True,
        message=f"{len(leads)} lead(s).",
        data={
            "leads": [
                {
                    "id": l.id,
                    "name": l.name,
                    "email": l.email,
                    "phone": l.phone,
                    "message": l.message,
                    "status": l.status,
                    "ai_summary": l.ai_summary,
                    "auto_reply_sent": l.auto_reply_sent,
                    "received_at": l.received_at.isoformat() if l.received_at else None,
                }
                for l in leads
            ]
        },
    )


@router.get("/{lead_id}", response_model=SuccessResponse)
async def get_lead(lead_id: str, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return SuccessResponse(
        success=True,
        message="Lead found.",
        data={
            "id": lead.id,
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "message": lead.message,
            "status": lead.status,
            "ai_summary": lead.ai_summary,
            "auto_reply_sent": lead.auto_reply_sent,
            "received_at": lead.received_at.isoformat() if lead.received_at else None,
        },
    )


async def _process_lead(
    client: anthropic.AsyncAnthropic,
    name: str,
    email: str,
    message: str,
) -> tuple[str, str]:
    """Returns (auto_reply_text, ai_summary)."""
    prompt = (
        f"A new lead came in for a small contracting business. Generate two things:\n\n"
        f"Lead name: {name}\n"
        f"Lead email: {email}\n"
        f"Their message: {message}\n\n"
        f"1. AUTO_REPLY: A warm, professional auto-response email (3-4 sentences). "
        f"Acknowledge their inquiry, let them know someone will follow up within 24 hours, "
        f"and mention they can also call if urgent. Sound human, not templated.\n\n"
        f"2. SUMMARY: A 2-sentence owner summary of this lead — what they want, "
        f"urgency level, and suggested next action.\n\n"
        f"Format your response exactly like this:\n"
        f"AUTO_REPLY:\n<reply text>\n\nSUMMARY:\n<summary text>"
    )

    resp = await client.messages.create(
        model=settings.claude_model,
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )

    text = resp.content[0].text.strip()

    auto_reply = ""
    summary = ""

    if "AUTO_REPLY:" in text and "SUMMARY:" in text:
        parts = text.split("SUMMARY:")
        auto_reply = parts[0].replace("AUTO_REPLY:", "").strip()
        summary = parts[1].strip()
    else:
        auto_reply = text
        summary = "New lead received. Review and follow up."

    return auto_reply, summary
