import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from genie.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Subcontractor(Base):
    __tablename__ = "subcontractors"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    skills: Mapped[list] = mapped_column(JSON, default=list)  # e.g. ["electrical", "plumbing"]
    hourly_rate: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    rating: Mapped[float] = mapped_column(Float, default=4.0)  # 0–5
    availability_status: Mapped[str] = mapped_column(String, default="available")  # available/busy/unavailable
    completed_jobs: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="assigned_subcontractor", foreign_keys="Job.assigned_subcontractor_id")
    schedules: Mapped[list["Schedule"]] = relationship("Schedule", back_populates="subcontractor")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="subcontractor")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    location: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    # pending / matching / assigned / in_progress / completed / at_risk / rescheduled / cancelled
    budget: Mapped[float] = mapped_column(Float, nullable=False)
    start_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    assigned_subcontractor_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("subcontractors.id"), nullable=True
    )
    priority: Mapped[str] = mapped_column(String, default="medium")  # low/medium/high/critical
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    assigned_subcontractor: Mapped[Optional["Subcontractor"]] = relationship(
        "Subcontractor", back_populates="jobs", foreign_keys=[assigned_subcontractor_id]
    )
    schedules: Mapped[list["Schedule"]] = relationship("Schedule", back_populates="job", cascade="all, delete-orphan")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="job", cascade="all, delete-orphan")
    risks: Mapped[list["Risk"]] = relationship("Risk", back_populates="job", cascade="all, delete-orphan")
    agent_logs: Mapped[list["AgentLog"]] = relationship("AgentLog", back_populates="job")


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id"), nullable=False)
    subcontractor_id: Mapped[str] = mapped_column(String, ForeignKey("subcontractors.id"), nullable=False)
    scheduled_start: Mapped[str] = mapped_column(String, nullable=False)  # ISO datetime string
    scheduled_end: Mapped[str] = mapped_column(String, nullable=False)
    actual_start: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    actual_end: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    job: Mapped["Job"] = relationship("Job", back_populates="schedules")
    subcontractor: Mapped["Subcontractor"] = relationship("Subcontractor", back_populates="schedules")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    job_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("jobs.id"), nullable=True)
    subcontractor_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("subcontractors.id"), nullable=True)
    direction: Mapped[str] = mapped_column(String, default="outbound")  # outbound/inbound
    channel: Mapped[str] = mapped_column(String, default="email")  # email/sms/slack
    subject: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="sent")  # sent/delivered/read/failed

    job: Mapped[Optional["Job"]] = relationship("Job", back_populates="messages")
    subcontractor: Mapped[Optional["Subcontractor"]] = relationship("Subcontractor", back_populates="messages")


class Risk(Base):
    __tablename__ = "risks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id"), nullable=False)
    risk_type: Mapped[str] = mapped_column(String, nullable=False)
    # weather/delay/no_show/budget/skills_gap/other
    severity: Mapped[str] = mapped_column(String, default="medium")  # low/medium/high/critical
    description: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    job: Mapped["Job"] = relationship("Job", back_populates="risks")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    agent_name: Mapped[str] = mapped_column(String, nullable=False)
    job_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("jobs.id"), nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    input_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tool_calls: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    job: Mapped[Optional["Job"]] = relationship("Job", back_populates="agent_logs")
