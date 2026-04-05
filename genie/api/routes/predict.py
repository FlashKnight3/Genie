"""Crystal Ball — AI-powered job success probability prediction."""
import json
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from genie.api.schemas import SuccessResponse
from genie.db.database import get_session
from genie.db.models import Job
from genie.tools.registry import ToolRegistry

router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("/{job_id}", response_model=SuccessResponse)
async def predict_job_success(job_id: str, db: AsyncSession = Depends(get_session)):
    """Run the PredictorAgent on a job and return a success probability with factors."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    from genie.agents.predictor import PredictorAgent

    registry = ToolRegistry(db)
    agent = PredictorAgent(db, registry)
    task = f"Predict success probability for job '{job.title}' (job_id: {job_id})"
    agent_result = await agent.run(task, context={"job_id": job_id}, max_iterations=8)

    # Parse the JSON prediction from the summary
    raw = agent_result.summary.strip()

    match = re.search(r"```(?:json)?\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        raw_json = match.group(1).strip()
    else:
        start = raw.find("{")
        end = raw.rfind("}")
        raw_json = raw[start:end + 1] if start != -1 and end != -1 else raw

    try:
        prediction = json.loads(raw_json)
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        prediction = {
            "success_probability": 50,
            "confidence": "low",
            "risk_factors": [{"factor": "Analysis incomplete", "impact": "medium", "detail": "Could not fully analyze job."}],
            "positive_factors": [],
            "recommendation": "Run the agent on this job first to gather more data.",
            "timeline_assessment": "at_risk",
        }

    # Normalize values
    prob = prediction.get("success_probability", 50)
    prediction["success_probability"] = max(5, min(95, int(prob)))
    prediction.setdefault("confidence", "medium")
    prediction.setdefault("risk_factors", [])
    prediction.setdefault("positive_factors", [])
    prediction.setdefault("recommendation", "")
    prediction.setdefault("timeline_assessment", "on_track")

    return SuccessResponse(
        success=True,
        message=f"Prediction complete: {prediction['success_probability']}% success probability.",
        data={"prediction": prediction, "job_id": job_id, "job_title": job.title},
    )
