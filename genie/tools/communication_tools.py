"""Tools for sending and managing communications with subcontractors."""
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.db.models import Message, Subcontractor


TOOL_DEFINITIONS = [
    {
        "name": "send_message",
        "description": "Send a message to a subcontractor and log it in the system.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subcontractor_id": {"type": "string"},
                "channel": {"type": "string", "description": "email, sms, or slack"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "job_id": {"type": "string", "description": "Associated job ID (optional)"},
            },
            "required": ["subcontractor_id", "channel", "subject", "body"],
        },
    },
    {
        "name": "get_message_thread",
        "description": "Get the full message thread between the system and a subcontractor for a job.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subcontractor_id": {"type": "string"},
                "job_id": {"type": "string"},
            },
            "required": ["subcontractor_id"],
        },
    },
    {
        "name": "get_subcontractor_contact",
        "description": "Get contact details (email, phone) for a subcontractor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subcontractor_id": {"type": "string"},
            },
            "required": ["subcontractor_id"],
        },
    },
    {
        "name": "mark_message_read",
        "description": "Mark a message as read.",
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string"},
            },
            "required": ["message_id"],
        },
    },
    {
        "name": "get_pending_responses",
        "description": "Get unread inbound messages for a job.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "log_inbound_message",
        "description": "Simulate an inbound reply from a subcontractor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subcontractor_id": {"type": "string"},
                "job_id": {"type": "string"},
                "body": {"type": "string"},
                "channel": {"type": "string"},
            },
            "required": ["subcontractor_id", "body"],
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

    # Simulate delivery confirmation
    return {
        "success": True,
        "message_id": msg.id,
        "recipient": sub.name,
        "channel": channel,
        "subject": subject,
        "delivery_status": "delivered",
    }


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
