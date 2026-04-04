"""Tools for sending and managing communications with subcontractors."""
import base64
import logging
import uuid
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.config import settings
from genie.db.models import Message, Subcontractor

logger = logging.getLogger(__name__)


TOOL_DEFINITIONS = [
    {
        "name": "send_message",
        "description": (
            "Send a message to a subcontractor via SMS or email and log it. "
            "Use channel='sms' for short urgent messages, 'email' for longer formal ones. "
            "Sends a real SMS via Twilio or real email via Resend when credentials are configured."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "subcontractor_id": {"type": "string"},
                "channel": {"type": "string", "description": "sms or email"},
                "subject": {"type": "string", "description": "SMS: used as log label only. Email: becomes the subject line."},
                "body": {"type": "string", "description": "The message text. Keep SMS under 160 characters."},
                "job_id": {"type": "string", "description": "Associated job ID"},
            },
            "required": ["subcontractor_id", "channel", "subject", "body"],
        },
    },
]


def _msg_to_dict(m: Message) -> dict:
    return {
        "id": m.id,
        "job_id": m.job_id,
        "subcontractor_id": m.subcontractor_id,
        "direction": m.direction,
        "channel": m.channel,
        "subject": m.subject,
        "body": m.body,
        "sent_at": m.sent_at.isoformat() if m.sent_at else None,
        "status": m.status,
    }


async def send_message(
    db: AsyncSession,
    subcontractor_id: str,
    channel: str,
    subject: str,
    body: str,
    job_id: str | None = None,
    attachments: list[dict] | None = None,
) -> dict:
    # Verify subcontractor exists
    result = await db.execute(select(Subcontractor).where(Subcontractor.id == subcontractor_id))
    sub = result.scalar_one_or_none()
    if not sub:
        return {"error": f"Subcontractor {subcontractor_id} not found"}

    msg = Message(
        id=str(uuid.uuid4()),
        job_id=job_id,
        subcontractor_id=subcontractor_id,
        direction="outbound",
        channel=channel,
        subject=subject,
        body=body,
        status="sent",
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # Attempt real delivery based on channel
    delivery_status = "simulated"
    delivery_error = None

    if channel == "sms" and settings.twilio_account_sid and settings.twilio_auth_token:
        try:
            delivery_status = await _send_twilio_sms(sub.phone, body)
        except Exception as exc:
            delivery_error = str(exc)
            logger.warning("Twilio SMS failed: %s", exc)
    elif channel == "email" and settings.resend_api_key:
        try:
            delivery_status = await _send_resend_email(sub.email, subject, body, attachments=attachments)
        except Exception as exc:
            delivery_error = str(exc)
            logger.warning("Resend email failed: %s", exc)

    result: dict = {
        "success": True,
        "message_id": msg.id,
        "recipient": sub.name,
        "channel": channel,
        "subject": subject,
        "delivery_status": delivery_status,
    }
    if delivery_error:
        result["delivery_error"] = delivery_error
    return result


async def get_message_thread(db: AsyncSession, subcontractor_id: str, job_id: str | None = None) -> dict:
    stmt = select(Message).where(Message.subcontractor_id == subcontractor_id)
    if job_id:
        stmt = stmt.where(Message.job_id == job_id)
    stmt = stmt.order_by(Message.sent_at)
    result = await db.execute(stmt)
    messages = result.scalars().all()
    return {"messages": [_msg_to_dict(m) for m in messages], "count": len(messages)}


async def get_subcontractor_contact(db: AsyncSession, subcontractor_id: str) -> dict:
    result = await db.execute(select(Subcontractor).where(Subcontractor.id == subcontractor_id))
    sub = result.scalar_one_or_none()
    if not sub:
        return {"error": f"Subcontractor {subcontractor_id} not found"}
    return {"name": sub.name, "email": sub.email, "phone": sub.phone, "location": sub.location}


async def mark_message_read(db: AsyncSession, message_id: str) -> dict:
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        return {"error": f"Message {message_id} not found"}
    msg.read_at = datetime.utcnow()
    msg.status = "read"
    await db.commit()
    return {"success": True, "message_id": message_id}


async def get_pending_responses(db: AsyncSession, job_id: str) -> dict:
    result = await db.execute(
        select(Message).where(
            Message.job_id == job_id,
            Message.direction == "inbound",
            Message.read_at.is_(None),
        )
    )
    messages = result.scalars().all()
    return {"pending": [_msg_to_dict(m) for m in messages], "count": len(messages)}


async def log_inbound_message(
    db: AsyncSession,
    subcontractor_id: str,
    body: str,
    job_id: str | None = None,
    channel: str = "email",
) -> dict:
    result = await db.execute(select(Subcontractor).where(Subcontractor.id == subcontractor_id))
    sub = result.scalar_one_or_none()
    name = sub.name if sub else "Unknown"

    msg = Message(
        id=str(uuid.uuid4()),
        job_id=job_id,
        subcontractor_id=subcontractor_id,
        direction="inbound",
        channel=channel,
        subject=f"Reply from {name}",
        body=body,
        status="delivered",
    )
    db.add(msg)
    await db.commit()
    return {"success": True, "message_id": msg.id, "from": name}


# ---------------------------------------------------------------------------
# Real delivery helpers
# ---------------------------------------------------------------------------

async def _send_twilio_sms(to_number: str, body: str) -> str:
    """Send SMS via Twilio REST API. Returns delivery status string."""
    credentials = base64.b64encode(
        f"{settings.twilio_account_sid}:{settings.twilio_auth_token}".encode()
    ).decode()

    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Basic {credentials}"},
            data={
                "From": settings.twilio_from_number,
                "To": to_number,
                "Body": body,
            },
        )
    data = resp.json()
    if resp.status_code not in (200, 201):
        raise RuntimeError(data.get("message", "Twilio error"))
    return data.get("status", "queued")


async def _send_resend_email(to_email: str, subject: str, body: str, attachments: list[dict] | None = None) -> str:
    """Send email via Resend API. Returns delivery status string."""
    payload = {
        "from": settings.resend_from_email,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }
    if attachments:
        payload["attachments"] = attachments

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if resp.status_code not in (200, 201):
        raise RuntimeError(resp.text)
    return "sent"
