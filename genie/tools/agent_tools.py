"""Tool for inter-agent delegation."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from genie.tools.registry import ToolRegistry


TOOL_DEFINITIONS = [
    {
        "name": "delegate_to_agent",
        "description": (
            "Delegate a task to a specialist agent. "
            "Available agents: 'matching' (find/assign subcontractors), "
            "'communication' (send messages to subcontractors), "
            "'risk' (assess and log risks for a job), "
            "'rescheduling' (reschedule disrupted jobs)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "One of: matching, communication, risk, rescheduling",
                },
                "task": {
                    "type": "string",
                    "description": "Natural language description of what the agent should do",
                },
                "context": {
                    "type": "object",
                    "description": "Key-value context to pass to the agent (e.g. job_id, subcontractor_id)",
                },
            },
            "required": ["agent_name", "task", "context"],
        },
    },
]


async def delegate_to_agent(
    db: "AsyncSession",
    registry: "ToolRegistry",
    agent_name: str,
    task: str,
    context: dict,
    _depth: int = 0,
) -> dict:
    """Instantiate and run a specialist agent. Max delegation depth = 1."""
    if _depth >= 1:
        return {"error": "Max delegation depth reached — cannot delegate further."}

    # Import here to avoid circular imports
    from genie.agents.communication import CommunicationAgent
    from genie.agents.matching import MatchingAgent
    from genie.agents.rescheduling import ReschedulingAgent
    from genie.agents.risk import RiskAgent

    agent_map = {
        "matching": MatchingAgent,
        "communication": CommunicationAgent,
        "risk": RiskAgent,
        "rescheduling": ReschedulingAgent,
    }

    if agent_name not in agent_map:
        return {"error": f"Unknown agent '{agent_name}'. Valid: {list(agent_map.keys())}"}

    agent_cls = agent_map[agent_name]
    # Create a child registry that prevents further delegation
    child_registry = registry.child_registry(_depth + 1)
    agent = agent_cls(db, child_registry)
    result = await agent.run(task, context)
    return {"agent": agent_name, "result": result.summary, "success": result.success}
