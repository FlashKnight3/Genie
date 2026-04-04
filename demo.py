"""
Genie Demo Script — End-to-end autonomous subcontractor management walkthrough.

Usage:
    python demo.py

Requires ANTHROPIC_API_KEY to be set in .env or environment.
"""
import asyncio
import json
import logging
import sys

logging.basicConfig(level=logging.WARNING)  # suppress SQLAlchemy noise during demo

DIVIDER = "─" * 70


def header(title: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  {title}")
    print(DIVIDER)


def section(label: str, data: dict | str) -> None:
    print(f"\n  [{label}]")
    if isinstance(data, dict):
        print(json.dumps(data, indent=4, default=str))
    else:
        print(f"  {data}")


async def run_demo():
    # ── Bootstrap ────────────────────────────────────────────────────────────
    from genie.db.database import AsyncSessionLocal, init_db
    from genie.db.seed import seed_database

    print("\n🔧 Initializing Genie database...")
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_database(session)

    # ── Fetch a few seed jobs ─────────────────────────────────────────────────
    header("STEP 1 — List pending jobs")
    async with AsyncSessionLocal() as db:
        from genie.tools.job_tools import list_jobs
        jobs_result = await list_jobs(db, status="pending")
        print(f"\n  Found {jobs_result['count']} pending jobs:")
        for j in jobs_result["jobs"][:3]:
            print(f"    • [{j['priority'].upper()}] {j['title']} — ${j['budget']:,.0f} — {j['location']}")

    if not jobs_result["jobs"]:
        print("  No jobs found. Exiting.")
        sys.exit(1)

    target_job = jobs_result["jobs"][0]
    job_id = target_job["id"]

    # ── PM Agent orchestrates the first job ───────────────────────────────────
    header(f"STEP 2 — PM Agent: Manage '{target_job['title']}'")
    print(f"\n  Job ID : {job_id}")
    print(f"  Skills : {target_job['required_skills']}")
    print(f"  Budget : ${target_job['budget']:,.0f}/job")
    print(f"  Dates  : {target_job['start_date']} → {target_job['end_date']}\n")

    async with AsyncSessionLocal() as db:
        from genie.agents.project_manager import ProjectManagerAgent
        from genie.tools.registry import ToolRegistry

        registry = ToolRegistry(db)
        pm = ProjectManagerAgent(db, registry)

        print("  Running PM Agent (this calls Claude — may take 30-60s)...")
        result = await pm.run(
            f"Manage this job end-to-end: '{target_job['title']}' (job_id: {job_id})",
            {"job_id": job_id},
        )

    section("PM Agent Result", {"success": result.success, "tool_calls": len(result.tool_calls_made)})
    print(f"\n  Summary:\n  {result.summary[:600]}")

    # ── Show updated job state ────────────────────────────────────────────────
    header("STEP 3 — Job state after PM Agent")
    async with AsyncSessionLocal() as db:
        from genie.tools.job_tools import get_job_timeline
        timeline = await get_job_timeline(db, job_id=job_id)

    section("Job", {
        "status": timeline["job"]["status"],
        "assigned_subcontractor_id": timeline["job"]["assigned_subcontractor_id"],
    })
    section("Schedules", timeline["schedules"])
    section("Risks", timeline["risks"])
    section("Agent actions", timeline["agent_actions"])

    # ── Show communications sent ──────────────────────────────────────────────
    header("STEP 4 — Communications log")
    async with AsyncSessionLocal() as db:
        from genie.tools.communication_tools import get_message_thread
        thread = await get_message_thread(db, subcontractor_id=timeline["job"]["assigned_subcontractor_id"] or "", job_id=job_id)

    if thread["count"] > 0:
        for msg in thread["messages"]:
            print(f"\n  [{msg['channel'].upper()} | {msg['direction']}] {msg['subject']}")
            print(f"  {msg['body'][:300]}")
    else:
        print("  No messages sent yet.")

    # ── Risk simulation ───────────────────────────────────────────────────────
    header("STEP 5 — Risk Agent: Simulate a weather risk")
    async with AsyncSessionLocal() as db:
        from genie.agents.risk import RiskAgent
        from genie.tools.registry import ToolRegistry

        registry = ToolRegistry(db)
        risk_agent = RiskAgent(db, registry)

        result = await risk_agent.run(
            f"Assess all risks for job_id: {job_id}. Check weather, subcontractor reliability, and schedule conflicts. "
            "Log any risks you find and recommend mitigation steps.",
            {"job_id": job_id},
        )

    section("Risk Agent Result", {"success": result.success, "tool_calls": len(result.tool_calls_made)})
    print(f"\n  Summary:\n  {result.summary[:600]}")

    # ── Rescheduling simulation ───────────────────────────────────────────────
    header("STEP 6 — Rescheduling Agent: Handle a disruption")
    async with AsyncSessionLocal() as db:
        from genie.agents.rescheduling import ReschedulingAgent
        from genie.tools.registry import ToolRegistry

        registry = ToolRegistry(db)
        resched = ReschedulingAgent(db, registry)

        result = await resched.run(
            f"The assigned subcontractor for job_id: {job_id} has reported a conflict. "
            "Find the next available slot and reschedule the job. Notify the subcontractor of the change.",
            {"job_id": job_id},
        )

    section("Rescheduling Agent Result", {"success": result.success, "tool_calls": len(result.tool_calls_made)})
    print(f"\n  Summary:\n  {result.summary[:600]}")

    # ── Final state ───────────────────────────────────────────────────────────
    header("STEP 7 — Final job state")
    async with AsyncSessionLocal() as db:
        from genie.tools.job_tools import get_job
        final = await get_job(db, job_id=job_id)

    section("Final Job", {
        "title": final["title"],
        "status": final["status"],
        "assigned_subcontractor_id": final.get("assigned_subcontractor_id"),
    })

    # ── Agent activity log ────────────────────────────────────────────────────
    header("STEP 8 — Agent activity log")
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        from genie.db.models import AgentLog
        result_logs = await db.execute(
            select(AgentLog).where(AgentLog.job_id == job_id).order_by(AgentLog.timestamp)
        )
        logs = result_logs.scalars().all()

    print(f"\n  {len(logs)} agent actions logged for this job:\n")
    for log in logs:
        calls = log.tool_calls or []
        tools_used = ", ".join(tc.get("tool", "?") for tc in calls) or "none"
        print(f"  [{log.agent_name:20s}] {log.action[:60]:60s} | tools: {tools_used}")

    print(f"\n{DIVIDER}")
    print("  Demo complete! Start the API server with: uvicorn main:app --reload")
    print(DIVIDER)


if __name__ == "__main__":
    asyncio.run(run_demo())
