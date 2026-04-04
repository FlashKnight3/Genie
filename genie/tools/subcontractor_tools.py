"""Tools for querying and managing subcontractors."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.db.models import Subcontractor


TOOL_DEFINITIONS = [
    {
        "name": "search_subcontractors",
        "description": "Search for subcontractors matching given skills, location, and rate/rating filters. Returns a list of candidates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "skills": {"type": "array", "items": {"type": "string"}, "description": "Skills required (at least one must match)"},
                "location": {"type": "string", "description": "Preferred location (city, state)"},
                "max_hourly_rate": {"type": "number", "description": "Maximum acceptable hourly rate"},
                "min_rating": {"type": "number", "description": "Minimum subcontractor rating (0-5)"},
                "availability_status": {"type": "string", "description": "Filter by availability: available, busy, unavailable"},
            },
            "required": [],
        },
    },
]


def _sub_to_dict(sub: Subcontractor) -> dict:
    return {
        "id": sub.id,
        "name": sub.name,
        "email": sub.email,
        "phone": sub.phone,
        "skills": sub.skills,
        "hourly_rate": sub.hourly_rate,
        "location": sub.location,
        "rating": sub.rating,
        "availability_status": sub.availability_status,
        "completed_jobs": sub.completed_jobs,
    }


async def search_subcontractors(
    db: AsyncSession,
    skills: list[str] | None = None,
    location: str | None = None,
    max_hourly_rate: float | None = None,
    min_rating: float | None = None,
    availability_status: str | None = None,
) -> dict:
    stmt = select(Subcontractor)
    if availability_status:
        stmt = stmt.where(Subcontractor.availability_status == availability_status)
    if max_hourly_rate is not None:
        stmt = stmt.where(Subcontractor.hourly_rate <= max_hourly_rate)
    if min_rating is not None:
        stmt = stmt.where(Subcontractor.rating >= min_rating)

    result = await db.execute(stmt)
    subs = result.scalars().all()

    # Filter by skills (any overlap)
    if skills:
        skills_lower = [s.lower() for s in skills]
        subs = [s for s in subs if any(sk.lower() in skills_lower for sk in (s.skills or []))]

    # Sort by rating desc
    subs = sorted(subs, key=lambda s: s.rating, reverse=True)

    return {"subcontractors": [_sub_to_dict(s) for s in subs], "count": len(subs)}


async def get_subcontractor(db: AsyncSession, subcontractor_id: str) -> dict:
    result = await db.execute(select(Subcontractor).where(Subcontractor.id == subcontractor_id))
    sub = result.scalar_one_or_none()
    if not sub:
        return {"error": f"Subcontractor {subcontractor_id} not found"}
    return _sub_to_dict(sub)


async def update_subcontractor_availability(db: AsyncSession, subcontractor_id: str, availability_status: str) -> dict:
    result = await db.execute(select(Subcontractor).where(Subcontractor.id == subcontractor_id))
    sub = result.scalar_one_or_none()
    if not sub:
        return {"error": f"Subcontractor {subcontractor_id} not found"}
    sub.availability_status = availability_status
    await db.commit()
    return {"success": True, "subcontractor_id": subcontractor_id, "new_status": availability_status}


async def rate_subcontractor(db: AsyncSession, subcontractor_id: str, new_rating: float) -> dict:
    result = await db.execute(select(Subcontractor).where(Subcontractor.id == subcontractor_id))
    sub = result.scalar_one_or_none()
    if not sub:
        return {"error": f"Subcontractor {subcontractor_id} not found"}
    sub.rating = round(new_rating, 2)
    sub.completed_jobs += 1
    await db.commit()
    return {"success": True, "subcontractor_id": subcontractor_id, "rating": sub.rating, "completed_jobs": sub.completed_jobs}
