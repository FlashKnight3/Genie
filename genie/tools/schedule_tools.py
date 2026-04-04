"""Tools for managing job schedules."""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.db.models import Schedule


TOOL_DEFINITIONS = [
    {
        "name": "get_schedule",
        "description": "Get schedule entries for a job.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "create_schedule",
        "description": "Create a schedule entry for a job-subcontractor pairing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "subcontractor_id": {"type": "string"},
                "scheduled_start": {"type": "string", "description": "ISO datetime string"},
                "scheduled_end": {"type": "string", "description": "ISO datetime string"},
                "notes": {"type": "string"},
            },
            "required": ["job_id", "subcontractor_id", "scheduled_start", "scheduled_end"],
        },
    },
    {
        "name": "update_schedule",
        "description": "Update an existing schedule entry with new start/end times.",
        "input_schema": {
            "type": "object",
            "properties": {
                "schedule_id": {"type": "string"},
                "new_start": {"type": "string", "description": "ISO datetime string"},
                "new_end": {"type": "string", "description": "ISO datetime string"},
                "notes": {"type": "string"},
            },
            "required": ["schedule_id"],
        },
    },
    {
        "name": "detect_conflicts",
        "description": "Check if a subcontractor has conflicting schedule entries during a given time window.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subcontractor_id": {"type": "string"},
                "start": {"type": "string", "description": "ISO datetime string"},
                "end": {"type": "string", "description": "ISO datetime string"},
            },
            "required": ["subcontractor_id", "start", "end"],
        },
    },
    {
        "name": "find_available_slots",
        "description": "Find available time slots for a subcontractor given a duration, earliest start, and deadline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subcontractor_id": {"type": "string"},
                "duration_hours": {"type": "number"},
                "earliest_start": {"type": "string", "description": "ISO date string"},
                "deadline": {"type": "string", "description": "ISO date string"},
            },
            "required": ["subcontractor_id", "duration_hours", "earliest_start", "deadline"],
        },
    },
]


def _sched_to_dict(s: Schedule) -> dict:
    return {
        "id": s.id,
        "job_id": s.job_id,
        "subcontractor_id": s.subcontractor_id,
        "scheduled_start": s.scheduled_start,
        "scheduled_end": s.scheduled_end,
        "actual_start": s.actual_start,
        "actual_end": s.actual_end,
        "notes": s.notes,
    }


async def get_schedule(db: AsyncSession, job_id: str) -> dict:
    result = await db.execute(select(Schedule).where(Schedule.job_id == job_id))
    schedules = result.scalars().all()
    return {"schedules": [_sched_to_dict(s) for s in schedules], "count": len(schedules)}


async def create_schedule(
    db: AsyncSession,
    job_id: str,
    subcontractor_id: str,
    scheduled_start: str,
    scheduled_end: str,
    notes: str | None = None,
) -> dict:
    sched = Schedule(
        id=str(uuid.uuid4()),
        job_id=job_id,
        subcontractor_id=subcontractor_id,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        notes=notes,
    )
    db.add(sched)
    await db.commit()
    await db.refresh(sched)
    return _sched_to_dict(sched)


async def update_schedule(
    db: AsyncSession,
    schedule_id: str,
    new_start: str | None = None,
    new_end: str | None = None,
    notes: str | None = None,
) -> dict:
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    sched = result.scalar_one_or_none()
    if not sched:
        return {"error": f"Schedule {schedule_id} not found"}
    if new_start:
        sched.scheduled_start = new_start
    if new_end:
        sched.scheduled_end = new_end
    if notes:
        sched.notes = notes
    await db.commit()
    return {"success": True, **_sched_to_dict(sched)}


async def detect_conflicts(db: AsyncSession, subcontractor_id: str, start: str, end: str) -> dict:
    result = await db.execute(
        select(Schedule).where(Schedule.subcontractor_id == subcontractor_id)
    )
    all_scheds = result.scalars().all()

    conflicts = []
    for s in all_scheds:
        # Overlap check: two intervals overlap if start1 < end2 AND start2 < end1
        if s.scheduled_start < end and s.scheduled_end > start:
            conflicts.append(_sched_to_dict(s))

    return {"has_conflicts": len(conflicts) > 0, "conflicts": conflicts, "count": len(conflicts)}


async def find_available_slots(
    db: AsyncSession,
    subcontractor_id: str,
    duration_hours: float,
    earliest_start: str,
    deadline: str,
) -> dict:
    result = await db.execute(
        select(Schedule).where(Schedule.subcontractor_id == subcontractor_id)
    )
    booked = result.scalars().all()
    booked_windows = [(s.scheduled_start, s.scheduled_end) for s in booked]

    # Generate candidate 8-hour work day slots between earliest_start and deadline
    slots = []
    try:
        current = datetime.fromisoformat(earliest_start)
        end_date = datetime.fromisoformat(deadline)
    except ValueError:
        # Try date-only format
        current = datetime.fromisoformat(earliest_start + "T08:00:00")
        end_date = datetime.fromisoformat(deadline + "T18:00:00")

    while current < end_date and len(slots) < 5:
        # Work hours 8am-6pm
        slot_start = current.replace(hour=8, minute=0, second=0)
        slot_end = slot_start + timedelta(hours=duration_hours)

        if slot_end.hour > 18:
            current += timedelta(days=1)
            continue

        slot_start_str = slot_start.isoformat()
        slot_end_str = slot_end.isoformat()

        # Check no overlap with booked windows
        overlaps = any(
            slot_start_str < bw[1] and slot_end_str > bw[0]
            for bw in booked_windows
        )
        if not overlaps:
            slots.append({"start": slot_start_str, "end": slot_end_str})

        current += timedelta(days=1)

    return {"available_slots": slots, "count": len(slots)}


async def get_full_schedule(db: AsyncSession) -> dict:
    result = await db.execute(select(Schedule))
    schedules = result.scalars().all()
    return {"schedules": [_sched_to_dict(s) for s in schedules], "count": len(schedules)}
