"""Pydantic request/response schemas for the API."""
from typing import Any, Optional
from pydantic import BaseModel, Field


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


class OrchestrateResponse(BaseModel):
    job_id: str
    agent: str
    success: bool
    summary: str
    tool_calls_count: int


# --- Generic ---

class SuccessResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict[str, Any]] = None
