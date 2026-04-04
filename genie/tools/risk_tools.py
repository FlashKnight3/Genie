"""Tools for risk detection, scoring, and management."""
import random
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.db.models import Job, Risk, Schedule, Subcontractor


TOOL_DEFINITIONS = [
    {
        "name": "get_weather_forecast",
        "description": "Get a simulated weather forecast for a location and date range. Returns conditions that may affect job execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string"},
                "start_date": {"type": "string", "description": "ISO date string"},
                "end_date": {"type": "string", "description": "ISO date string"},
            },
            "required": ["location", "start_date"],
        },
    },
    {
        "name": "check_subcontractor_reliability",
        "description": "Check historical reliability of a subcontractor based on rating and job history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "subcontractor_id": {"type": "string"},
            },
            "required": ["subcontractor_id"],
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
        "name": "resolve_risk",
        "description": "Mark a risk as resolved with a description of the action taken.",
        "input_schema": {
            "type": "object",
            "properties": {
                "risk_id": {"type": "string"},
                "resolution_action": {"type": "string"},
            },
            "required": ["risk_id", "resolution_action"],
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
    {
        "name": "detect_schedule_conflicts",
        "description": "Check if the assigned subcontractor has overlapping scheduled jobs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string"},
            },
            "required": ["job_id"],
        },
    },
]

# Simulated weather patterns for demo purposes
_WEATHER_SCENARIOS = [
    {"condition": "Clear", "temp_f": 78, "wind_mph": 8, "precipitation_chance": 5, "risk_level": "low"},
    {"condition": "Partly Cloudy", "temp_f": 72, "wind_mph": 12, "precipitation_chance": 20, "risk_level": "low"},
    {"condition": "Thunderstorms", "temp_f": 68, "wind_mph": 35, "precipitation_chance": 85, "risk_level": "high"},
    {"condition": "Heavy Rain", "temp_f": 65, "wind_mph": 22, "precipitation_chance": 90, "risk_level": "high"},
    {"condition": "Extreme Heat", "temp_f": 105, "wind_mph": 5, "precipitation_chance": 2, "risk_level": "medium"},
    {"condition": "Overcast", "temp_f": 70, "wind_mph": 10, "precipitation_chance": 30, "risk_level": "low"},
]


async def get_weather_forecast(
    db: AsyncSession,
    location: str,
    start_date: str,
    end_date: str | None = None,
) -> dict:
    # Deterministic-ish simulation based on location hash
    seed = sum(ord(c) for c in location + start_date) % len(_WEATHER_SCENARIOS)
    forecast = _WEATHER_SCENARIOS[seed]
    return {
        "location": location,
        "start_date": start_date,
        "end_date": end_date or start_date,
        "forecast": forecast,
        "advisory": "Outdoor work not recommended." if forecast["risk_level"] == "high" else "Conditions acceptable for work.",
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
