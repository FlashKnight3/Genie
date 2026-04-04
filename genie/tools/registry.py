"""Central tool registry and dispatcher."""
from __future__ import annotations

import logging
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Maps agent name → set of tool names that agent has access to
AGENT_TOOL_PERMISSIONS: dict[str, set[str]] = {
    "project_manager": {
        "get_job", "update_job_status", "list_jobs", "get_job_timeline",
        "assign_subcontractor", "get_active_risks", "calculate_risk_score",
        "delegate_to_agent",
    },
    "matching": {
        "search_subcontractors", "get_subcontractor", "update_subcontractor_availability",
        "check_subcontractor_schedule", "assign_subcontractor",
        "get_job", "detect_conflicts",
    },
    "communication": {
        "send_message", "get_message_thread", "get_subcontractor_contact",
        "mark_message_read", "get_pending_responses", "log_inbound_message",
        "get_job",
    },
    "risk": {
        "get_weather_forecast", "check_subcontractor_reliability", "calculate_risk_score",
        "create_risk_record", "resolve_risk", "get_active_risks",
        "detect_schedule_conflicts", "get_job", "update_job_status",
    },
    "rescheduling": {
        "get_schedule", "create_schedule", "update_schedule", "find_available_slots",
        "detect_conflicts", "get_job", "update_job_status",
        "search_subcontractors", "assign_subcontractor",
        "send_message", "get_subcontractor_contact",
        "create_risk_record", "resolve_risk",
    },
}

# Alias tool names used by agents
_ALIASES: dict[str, str] = {
    "check_subcontractor_schedule": "detect_conflicts",
    "get_active_risks": "get_active_risks",
}


class ToolRegistry:
    def __init__(self, db: AsyncSession, depth: int = 0) -> None:
        self._db = db
        self._depth = depth
        self._tools: dict[str, Callable] = {}
        self._schemas: dict[str, dict] = {}
        self._register_all()

    def _register_all(self) -> None:
        from genie.tools import (
            agent_tools,
            communication_tools,
            job_tools,
            risk_tools,
            schedule_tools,
            subcontractor_tools,
        )

        modules = [
            subcontractor_tools,
            job_tools,
            schedule_tools,
            communication_tools,
            risk_tools,
            agent_tools,
        ]

        for mod in modules:
            for schema in mod.TOOL_DEFINITIONS:
                name = schema["name"]
                fn = getattr(mod, name, None)
                if fn is None:
                    logger.warning("Tool function '%s' not found in module %s", name, mod.__name__)
                    continue
                self._tools[name] = fn
                self._schemas[name] = schema

    def get_schemas_for_agent(self, agent_name: str) -> list[dict]:
        allowed = AGENT_TOOL_PERMISSIONS.get(agent_name, set())
        return [self._schemas[n] for n in allowed if n in self._schemas]

    async def call(self, tool_name: str, tool_input: dict) -> Any:
        # Resolve alias
        resolved = _ALIASES.get(tool_name, tool_name)
        fn = self._tools.get(resolved)
        if fn is None:
            return {"error": f"Tool '{tool_name}' not found"}

        try:
            import inspect
            sig = inspect.signature(fn)
            params = set(sig.parameters.keys())

            kwargs: dict[str, Any] = {}

            # Always inject db
            if "db" in params:
                kwargs["db"] = self._db

            # Inject registry for delegate_to_agent
            if "registry" in params:
                kwargs["registry"] = self

            # Inject depth for recursion guard
            if "_depth" in params:
                kwargs["_depth"] = self._depth

            # Merge caller-provided inputs
            for k, v in tool_input.items():
                kwargs[k] = v

            result = fn(**kwargs)
            if inspect.iscoroutine(result):
                result = await result
            return result
        except Exception as exc:
            logger.exception("Tool '%s' raised an exception", tool_name)
            return {"error": str(exc)}

    def child_registry(self, depth: int) -> "ToolRegistry":
        """Create a child registry with increased depth (limits further delegation)."""
        child = ToolRegistry.__new__(ToolRegistry)
        child._db = self._db
        child._depth = depth
        child._tools = self._tools
        child._schemas = self._schemas
        return child
