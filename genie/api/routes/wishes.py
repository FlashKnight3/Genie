"""Make a Wish — natural language job creation powered by Claude."""
import anthropic
import json
import re
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from genie.api.schemas import SuccessResponse
from genie.config import settings
from genie.db.database import get_session
from genie.tools.job_tools import create_job

router = APIRouter(prefix="/wishes", tags=["wishes"])


class WishRequest(BaseModel):
    wish: str


@router.post("", response_model=SuccessResponse, status_code=201)
async def make_wish(body: WishRequest, db: AsyncSession = Depends(get_session)):
    """Convert a natural-language wish into a structured job using Claude."""
    if not body.wish.strip():
        raise HTTPException(status_code=400, detail="Wish cannot be empty.")

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    today = date.today().isoformat()

    prompt = (
        f"Today's date is {today}.\n\n"
        f"User wish: {body.wish}\n\n"
        "You are a job intake specialist. Extract the job details from the user's wish and return "
        "a JSON object with EXACTLY these fields:\n\n"
        "{\n"
        '  "title": "short job title (5-8 words)",\n'
        '  "description": "detailed description expanding on the wish (2-4 sentences)",\n'
        '  "required_skills": ["skill1", "skill2"],\n'
        '  "location": "City, State (default to Austin, TX if not specified)",\n'
        '  "budget": 0,\n'
        '  "start_date": "YYYY-MM-DD (default to today if not specified)",\n'
        '  "end_date": "YYYY-MM-DD (infer from relative phrases like \'end of April\', \'by Friday\', \'in 2 weeks\')",\n'
        '  "priority": "low|medium|high|critical (infer from urgency words like ASAP, urgent, emergency)"\n'
        "}\n\n"
        "Rules:\n"
        "- budget: extract number from text, or estimate a realistic market rate if not given\n"
        "- required_skills: infer from job type (e.g. 'electrician' → ['electrical'], 'plumber' → ['plumbing'])\n"
        "- priority: 'critical' for emergency/ASAP, 'high' for urgent, 'medium' default, 'low' for flexible\n"
        "- Return ONLY valid JSON, nothing else."
    )

    resp = await client.messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.content[0].text.strip()

    # Extract JSON from response
    match = re.search(r"```(?:json)?\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        raw_json = match.group(1).strip()
    else:
        start = raw.find("{")
        end = raw.rfind("}")
        raw_json = raw[start:end + 1] if start != -1 and end != -1 else raw

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Could not parse job details from your wish. Please be more specific.")

    # Validate required fields
    if not parsed.get("title") or not parsed.get("description") or not parsed.get("location"):
        raise HTTPException(status_code=422, detail="Could not extract required job details. Please be more specific.")

    # Create the job
    job = await create_job(
        db,
        title=parsed.get("title", "New Job"),
        description=parsed.get("description", body.wish),
        location=parsed.get("location", "Austin, TX"),
        budget=float(parsed.get("budget", 0)),
        required_skills=parsed.get("required_skills", []),
        start_date=parsed.get("start_date"),
        end_date=parsed.get("end_date"),
        priority=parsed.get("priority", "medium"),
    )

    if "error" in job:
        raise HTTPException(status_code=400, detail=job["error"])

    return SuccessResponse(
        success=True,
        message=f"Wish granted! Job '{parsed['title']}' created.",
        data={"parsed": parsed, "job": job},
    )
