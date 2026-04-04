"""Quote builder — AI-drafted line-item quotes from job description."""
import anthropic
import json
import re
from fastapi import APIRouter
from pydantic import BaseModel

from genie.api.schemas import SuccessResponse
from genie.config import settings

router = APIRouter(prefix="/quote", tags=["quote"])


class QuoteRequest(BaseModel):
    description: str
    location: str | None = None
    budget_hint: float | None = None


@router.post("", response_model=SuccessResponse)
async def draft_quote(body: QuoteRequest):
    """Generate a line-item quote draft from a plain-English job description."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    context_parts = [f"Job description: {body.description}"]
    if body.location:
        context_parts.append(f"Location: {body.location}")
    if body.budget_hint:
        context_parts.append(f"Expected budget range: ~${body.budget_hint:,.0f}")

    prompt = (
        "\n".join(context_parts) + "\n\n"
        "You are a professional contractor estimator. Based on this job description, "
        "generate a realistic line-item quote. Return a JSON object with this exact structure:\n\n"
        "{\n"
        '  "title": "Quote title",\n'
        '  "summary": "1-2 sentence overview of the work",\n'
        '  "line_items": [\n'
        '    {"item": "item name", "description": "brief detail", "qty": 1, "unit": "ea/hr/sf/lf", "unit_price": 0.00, "total": 0.00}\n'
        "  ],\n"
        '  "subtotal": 0.00,\n'
        '  "tax_rate": 0.08,\n'
        '  "tax": 0.00,\n'
        '  "total": 0.00,\n'
        '  "notes": "any important caveats or assumptions"\n'
        "}\n\n"
        "Use realistic market rates for Austin, TX (or the specified location). "
        "Include 5-10 line items covering labor, materials, and any permits/fees. "
        "Return only valid JSON, nothing else."
    )

    resp = await client.messages.create(
        model=settings.claude_model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.content[0].text.strip()

    match = re.search(r"```(?:json)?\n?(.*?)\n?```", raw, re.DOTALL)
    if match:
        raw_json = match.group(1).strip()
    else:
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            raw_json = raw[start:end+1]
        else:
            raw_json = raw

    try:
        quote = json.loads(raw_json)
    except json.JSONDecodeError:
        quote = {"raw": raw, "parse_error": "Could not parse as JSON — raw text returned"}

    return SuccessResponse(
        success=True,
        message="Quote drafted.",
        data={"quote": quote},
    )
