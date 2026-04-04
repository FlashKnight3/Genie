"""Tools for risk detection, scoring, and management."""
import logging
import uuid
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.db.models import Job, Risk, Schedule, Subcontractor

logger = logging.getLogger(__name__)


TOOL_DEFINITIONS = [
    {
        "name": "get_weather_forecast",
        "description": "Get a real weather forecast for a location and date range (uses Open-Meteo). Returns conditions that may affect job execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City and state, e.g. 'Austin, TX'"},
                "start_date": {"type": "string", "description": "ISO date string YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "ISO date string YYYY-MM-DD (optional, defaults to start_date)"},
            },
            "required": ["location", "start_date"],
        },
    },
    {
        "name": "calculate_risk_score",
        "description": "Calculate a composite risk score (0-100) for a job. Higher = more risky.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
            },
            "required": ["job_id"],
        },
    },
    {
        "name": "create_risk_record",
        "description": "Log a risk event for a job.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
                "risk_type": {"type": "string", "description": "weather, delay, no_show, budget, skills_gap, other"},
                "severity": {"type": "string", "description": "low, medium, high, or critical"},
                "description": {"type": "string"},
            },
            "required": ["job_id", "risk_type", "severity", "description"],
        },
    },
    {
        "name": "get_active_risks",
        "description": "Get all unresolved risks for a job.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
            },
            "required": ["job_id"],
        },
    },
]

# WMO weather interpretation codes → human-readable + risk level
_WMO_CODES: dict[int, tuple[str, str]] = {
    0: ("Clear sky", "low"),
    1: ("Mainly clear", "low"), 2: ("Partly cloudy", "low"), 3: ("Overcast", "low"),
    45: ("Fog", "medium"), 48: ("Icing fog", "medium"),
    51: ("Light drizzle", "low"), 53: ("Moderate drizzle", "low"), 55: ("Dense drizzle", "medium"),
    61: ("Slight rain", "low"), 63: ("Moderate rain", "medium"), 65: ("Heavy rain", "high"),
    71: ("Slight snow", "medium"), 73: ("Moderate snow", "high"), 75: ("Heavy snow", "high"),
    80: ("Slight showers", "low"), 81: ("Moderate showers", "medium"), 82: ("Violent showers", "high"),
    95: ("Thunderstorm", "high"), 96: ("Thunderstorm + hail", "high"), 99: ("Thunderstorm + heavy hail", "high"),
}


async def get_weather_forecast(
    db: AsyncSession,
    location: str,
    start_date: str,
    end_date: str | None = None,
) -> dict:
    """Fetch real weather data from Open-Meteo (free, no API key required)."""
    end = end_date or start_date

    # Geocoding API needs just the city name — strip ", TX" style suffixes
    city_name = location.split(",")[0].strip()

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            # Step 1: geocode the location string
            geo_resp = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city_name, "count": 1, "language": "en", "format": "json"},
            )
            geo_data = geo_resp.json()
            results = geo_data.get("results") or []
            if not results:
                return {"error": f"Could not geocode location: {location}", "location": location}

            lat = results[0]["latitude"]
            lon = results[0]["longitude"]
            resolved_name = results[0].get("name", location)

            # Step 2: fetch daily forecast
            wx_resp = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "weathercode,temperature_2m_max,windspeed_10m_max,precipitation_sum",
                    "temperature_unit": "fahrenheit",
                    "windspeed_unit": "mph",
                    "precipitation_unit": "inch",
                    "timezone": "America/Chicago",
                    "start_date": start_date,
                    "end_date": end,
                },
            )
            wx_data = wx_resp.json()
    except Exception as exc:
        logger.warning("Open-Meteo request failed: %s", exc)
        return {
            "location": location,
            "start_date": start_date,
            "end_date": end,
            "error": "Weather API unavailable — assume acceptable conditions.",
        }

    daily = wx_data.get("daily", {})
    dates = daily.get("time", [])
    codes = daily.get("weathercode", [])
    max_temps = daily.get("temperature_2m_max", [])
    wind_speeds = daily.get("windspeed_10m_max", [])
    precip = daily.get("precipitation_sum", [])

    days = []
    worst_risk = "low"
    risk_order = {"low": 0, "medium": 1, "high": 2}

    for i, date in enumerate(dates):
        code = codes[i] if i < len(codes) else 0
        condition, risk = _WMO_CODES.get(code, ("Unknown", "low"))
        temp = max_temps[i] if i < len(max_temps) else None
        wind = wind_speeds[i] if i < len(wind_speeds) else None
        rain = precip[i] if i < len(precip) else None

        # Extreme heat is a risk too
        if temp and temp >= 100:
            risk = "high" if risk_order[risk] < risk_order["high"] else risk
            condition = f"Extreme heat ({temp:.0f}°F)"

        if risk_order.get(risk, 0) > risk_order.get(worst_risk, 0):
            worst_risk = risk

        days.append({
            "date": date,
            "condition": condition,
            "temp_max_f": round(temp, 1) if temp is not None else None,
            "wind_mph": round(wind, 1) if wind is not None else None,
            "precip_in": round(rain, 2) if rain is not None else None,
            "risk_level": risk,
        })

    advisories = {
        "low": "Conditions acceptable for work.",
        "medium": "Monitor conditions — some disruption possible.",
        "high": "Outdoor work not recommended during affected days.",
    }

    return {
        "location": resolved_name,
        "start_date": start_date,
        "end_date": end,
        "days": days,
        "worst_risk_level": worst_risk,
        "advisory": advisories[worst_risk],
    }


async def check_subcontractor_reliability(db: AsyncSession, subcontractor_id: str) -> dict:
    result = await db.execute(select(Subcontractor).where(Subcontractor.id == subcontractor_id))
    sub = result.scalar_one_or_none()
    if not sub:
        return {"error": f"Subcontractor {subcontractor_id} not found"}

    # Derive reliability from rating and completed_jobs
    no_show_rate = max(0.0, round((5.0 - sub.rating) * 0.05, 3))
    cancellation_rate = max(0.0, round((5.0 - sub.rating) * 0.04, 3))
    reliability_score = round(sub.rating / 5.0 * 100, 1)

    return {
        "subcontractor_id": subcontractor_id,
        "name": sub.name,
        "rating": sub.rating,
        "completed_jobs": sub.completed_jobs,
        "estimated_no_show_rate": no_show_rate,
        "estimated_cancellation_rate": cancellation_rate,
        "reliability_score": reliability_score,
    }


async def calculate_risk_score(db: AsyncSession, job_id: str) -> dict:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        return {"error": f"Job {job_id} not found"}

    score = 0
    factors = []

    # Factor 1: No subcontractor assigned
    if not job.assigned_subcontractor_id:
        score += 30
        factors.append({"factor": "no_subcontractor_assigned", "points": 30})
    else:
        sub_result = await db.execute(select(Subcontractor).where(Subcontractor.id == job.assigned_subcontractor_id))
        sub = sub_result.scalar_one_or_none()
        if sub and sub.rating < 4.0:
            pts = int((4.0 - sub.rating) * 15)
            score += pts
            factors.append({"factor": "low_subcontractor_rating", "points": pts, "rating": sub.rating})

    # Factor 2: Overdue
    if job.end_date:
        today = datetime.utcnow().date().isoformat()
        if job.end_date < today and job.status not in ("completed", "cancelled"):
            score += 25
            factors.append({"factor": "past_deadline", "points": 25})

    # Factor 3: Active unresolved risks
    risk_result = await db.execute(
        select(Risk).where(Risk.job_id == job_id, Risk.resolved_at.is_(None))
    )
    active_risks = risk_result.scalars().all()
    severity_pts = {"low": 5, "medium": 10, "high": 20, "critical": 35}
    for r in active_risks:
        pts = severity_pts.get(r.severity, 10)
        score += pts
        factors.append({"factor": f"active_risk_{r.risk_type}", "points": pts})

    # Factor 4: Schedule conflicts
    if job.assigned_subcontractor_id and job.start_date and job.end_date:
        conflict_result = await db.execute(
            select(Schedule).where(
                Schedule.subcontractor_id == job.assigned_subcontractor_id,
                Schedule.job_id != job_id,
                Schedule.scheduled_start < job.end_date,
                Schedule.scheduled_end > job.start_date,
            )
        )
        conflicts = conflict_result.scalars().all()
        if conflicts:
            score += 15
            factors.append({"factor": "schedule_conflict", "points": 15})

    score = min(score, 100)
    level = "low" if score <= 30 else "medium" if score <= 60 else "high" if score <= 80 else "critical"

    return {
        "job_id": job_id,
        "risk_score": score,
        "risk_level": level,
        "factors": factors,
        "recommendation": (
            "Monitor closely." if level == "medium"
            else "Alert PM — intervention needed." if level == "high"
            else "CRITICAL — escalate and reschedule immediately." if level == "critical"
            else "No immediate action required."
        ),
    }


async def create_risk_record(
    db: AsyncSession,
    job_id: str,
    risk_type: str,
    severity: str,
    description: str,
) -> dict:
    risk = Risk(
        id=str(uuid.uuid4()),
        job_id=job_id,
        risk_type=risk_type,
        severity=severity,
        description=description,
    )
    db.add(risk)
    await db.commit()
    await db.refresh(risk)
    return {
        "success": True,
        "risk_id": risk.id,
        "job_id": job_id,
        "risk_type": risk_type,
        "severity": severity,
    }


async def resolve_risk(db: AsyncSession, risk_id: str, resolution_action: str) -> dict:
    result = await db.execute(select(Risk).where(Risk.id == risk_id))
    risk = result.scalar_one_or_none()
    if not risk:
        return {"error": f"Risk {risk_id} not found"}
    risk.resolved_at = datetime.utcnow()
    risk.resolution_action = resolution_action
    await db.commit()
    return {"success": True, "risk_id": risk_id, "resolved_at": risk.resolved_at.isoformat()}


async def get_active_risks(db: AsyncSession, job_id: str) -> dict:
    result = await db.execute(
        select(Risk).where(Risk.job_id == job_id, Risk.resolved_at.is_(None))
    )
    risks = result.scalars().all()
    return {
        "risks": [
            {
                "id": r.id,
                "risk_type": r.risk_type,
                "severity": r.severity,
                "description": r.description,
                "triggered_at": r.triggered_at.isoformat() if r.triggered_at else None,
            }
            for r in risks
        ],
        "count": len(risks),
    }


async def detect_schedule_conflicts(db: AsyncSession, job_id: str) -> dict:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job or not job.assigned_subcontractor_id:
        return {"has_conflicts": False, "conflicts": []}

    conflict_result = await db.execute(
        select(Schedule).where(
            Schedule.subcontractor_id == job.assigned_subcontractor_id,
            Schedule.job_id != job_id,
        )
    )
    other_schedules = conflict_result.scalars().all()

    conflicts = []
    for s in other_schedules:
        if job.start_date and job.end_date:
            if s.scheduled_start < job.end_date and s.scheduled_end > job.start_date:
                conflicts.append({"schedule_id": s.id, "conflicting_job_id": s.job_id})

    return {"has_conflicts": len(conflicts) > 0, "conflicts": conflicts}
