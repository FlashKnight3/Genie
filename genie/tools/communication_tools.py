"""Tools for sending and managing communications with subcontractors."""
import base64
import html
import logging
import uuid
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.config import settings
from genie.db.models import Message, Subcontractor

logger = logging.getLogger(__name__)


def twilio_sms_configured() -> bool:
    """True when outbound SMS can be sent (account creds + From or Messaging Service)."""
    if not settings.twilio_account_sid.strip() or not settings.twilio_auth_token.strip():
        return False
    return bool(settings.twilio_from_number.strip()) or bool(settings.twilio_messaging_service_sid.strip())


def normalize_phone_e164(phone: str) -> str | None:
    """Normalize stored phone strings to E.164 for Twilio.

    Accepts numbers that already include a leading +, or US 10-digit / 1+10-digit forms.
    Non-US numbers should be stored with country code and leading +.
    """
    p = (phone or "").strip()
    if not p:
        return None
    if p.startswith("+"):
        digits = "".join(c for c in p if c.isdigit())
        return f"+{digits}" if len(digits) >= 10 else None
    digits = "".join(c for c in p if c.isdigit())
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    if len(digits) >= 10:
        return f"+{digits}"
    return None


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


def truncate_for_sms(text: str, max_len: int = 320) -> str:
    """Keep SMS payloads short for delivery and cost."""
    t = (text or "").strip().replace("\n", " ")
    if len(t) <= max_len:
        return t
    return t[: max_len - 1].rstrip() + "…"


async def notify_assigned_subcontractor_after_orchestrate(
    db: AsyncSession,
    *,
    job_id: str,
    job_title: str,
    job_status: str,
    subcontractor_id: str,
    agent_summary: str,
    schedule_summary: str | None = None,
) -> dict:
    """Send both SMS (Twilio) and email (Resend) when configured — called after every /orchestrate.

    Logs two outbound Message rows (one per channel). Each channel is attempted independently.
    """
    subject = f"Genie update: {job_title}"
    email_lines = [
        f"Job: {job_title}",
        f"Status: {job_status}",
        "",
        "Latest project manager run:",
        (agent_summary or "(no summary)").strip(),
    ]
    if schedule_summary:
        email_lines.extend(["", schedule_summary])
    email_body = "\n".join(email_lines)
    sms_body = truncate_for_sms(f"{job_title} — {job_status}. {agent_summary or ''}")

    sms_result = await send_message(
        db, subcontractor_id, "sms", subject, sms_body, job_id=job_id
    )
    email_result = await send_message(
        db, subcontractor_id, "email", subject, email_body, job_id=job_id
    )
    return {"sms": sms_result, "email": email_result}


async def send_message(
    db: AsyncSession,
    subcontractor_id: str,
    channel: str,
    subject: str,
    body: str,
    job_id: str | None = None,
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

    if channel == "sms" and twilio_sms_configured():
        try:
            delivery_status = await _send_twilio_sms(sub.phone, body)
        except Exception as exc:
            delivery_error = str(exc)
            logger.warning("Twilio SMS failed: %s", exc)
    elif channel == "email" and settings.resend_api_key.strip():
        try:
            delivery_status = await _send_resend_email(sub.email, subject, body)
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
    to_e164 = normalize_phone_e164(to_number)
    if not to_e164:
        raise ValueError(
            "Invalid or missing phone; use E.164 (e.g. +15125550100) or a 10-digit US number."
        )

    msid = settings.twilio_messaging_service_sid.strip()
    from_num = settings.twilio_from_number.strip()
    if msid and not msid.upper().startswith("MG"):
        raise ValueError(
            "TWILIO_MESSAGING_SERVICE_SID must be a Messaging Service SID (starts with MG). "
            "Secret keys (SK…) belong in TWILIO_AUTH_TOKEN, not here."
        )
    form: dict[str, str] = {"To": to_e164, "Body": body}
    if msid:
        form["MessagingServiceSid"] = msid
        if from_num:
            form["From"] = from_num
    else:
        form["From"] = from_num

    credentials = base64.b64encode(
        f"{settings.twilio_account_sid}:{settings.twilio_auth_token}".encode()
    ).decode()

    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Basic {credentials}"},
            data=form,
        )
    try:
        data = resp.json()
    except Exception:
        resp.raise_for_status()
        raise RuntimeError(resp.text or "Twilio error")
    if resp.status_code not in (200, 201):
        err = data.get("message") if isinstance(data, dict) else None
        code = data.get("code") if isinstance(data, dict) else None
        suffix = f" (code {code})" if code else ""
        raise RuntimeError(f"{err or 'Twilio error'}{suffix}")
    if not isinstance(data, dict):
        return "queued"
    return str(data.get("status", "queued"))


def _plain_to_html_email(body: str) -> str:
    """Minimal HTML body from plain text (same idea as Resend SDK html: '<p>…</p>')."""
    safe = html.escape(body or "")
    paras = safe.split("\n\n")
    inner = "".join(f"<p>{p.replace(chr(10), '<br/>')}</p>" for p in paras if p.strip()) or "<p></p>"
    return inner


async def _send_resend_email(to_email: str, subject: str, body: str) -> str:
    """Send email via Resend HTTP API using RESEND_API_KEY and RESEND_FROM_EMAIL from .env."""
    key = settings.resend_api_key.strip()
    if not key:
        raise ValueError("Set RESEND_API_KEY in .env (Resend dashboard → API Keys).")

    from_addr = (settings.resend_from_email or "").strip() or "onboarding@resend.dev"
    payload = {
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "text": body,
        "html": _plain_to_html_email(body),
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    if resp.status_code not in (200, 201):
        raise RuntimeError(resp.text)
    return "sent"
