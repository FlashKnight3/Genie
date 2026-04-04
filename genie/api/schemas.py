"""Pydantic request/response schemas for the API."""
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


# --- Jobs ---

class JobCreate(BaseModel):
    title: str
    description: str
    location: str
    budget: float
    required_skills: list[str] = Field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    priority: str = "medium"


class JobStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class JobResponse(BaseModel):
    id: str
    title: str
    description: str
    required_skills: list[str]
    location: str
    status: str
    budget: float
    start_date: Optional[str]
    end_date: Optional[str]
    priority: str
    assigned_subcontractor_id: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]


# --- Subcontractors ---

class SubcontractorCreate(BaseModel):
    name: str
    email: str
    phone: str
    skills: list[str] = Field(default_factory=list)
    hourly_rate: float
    location: str
    rating: float = 4.0


class SubcontractorResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    skills: list[str]
    hourly_rate: float
    location: str
    rating: float
    availability_status: str
    completed_jobs: int


# --- Orchestration ---

class OrchestrateRequest(BaseModel):
    job_id: str
    task: Optional[str] = None  # defaults to "manage this job end-to-end"
    # Optional caps (clamped server-side to orchestrate_*_cap in settings)
    max_llm_rounds: Optional[int] = Field(
        default=None,
        ge=1,
        description="Max tool-use rounds for the project manager on this run",
    )
    max_specialist_agents: Optional[int] = Field(
        default=None,
        ge=0,
        description="Max delegate_to_agent (specialist) runs allowed this orchestration",
    )
    max_rounds_per_specialist: Optional[int] = Field(
        default=None,
        ge=1,
        description="Max tool-use rounds per specialist agent",
    )

    @field_validator("max_llm_rounds", "max_specialist_agents", "max_rounds_per_specialist", mode="before")
    @classmethod
    def empty_as_none(cls, v: Any) -> Any:
        return None if v in ("", None) else v


class OrchestrateResponse(BaseModel):
    job_id: str
    agent: str
    success: bool
    summary: str
    tool_calls_count: int


# --- User profile / onboarding ---

class UserProfileOut(BaseModel):
    user_id: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    company_name: Optional[str] = None
    onboarding_completed: bool = False


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    company_name: Optional[str] = None
    onboarding_completed: Optional[bool] = None


# --- Generic ---

class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict[str, Any]] = None
