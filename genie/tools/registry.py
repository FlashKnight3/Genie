"""Central tool registry and dispatcher."""
from __future__ import annotations

import logging
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from genie.config import settings

logger = logging.getLogger(__name__)


class DelegateBudget:
    """Mutable budget for delegate_to_agent calls in one orchestration."""

    def __init__(self, remaining: int) -> None:
        self.remaining = max(0, remaining)

    def try_consume(self) -> bool:
        if self.remaining <= 0:
            return False
        self.remaining -= 1
        return True

# Maps agent name → set of tool names that agent has access to.
# Keep each set small — every extra tool adds tokens to every prompt and
# gives Claude more ways to go off-script.
AGENT_TOOL_PERMISSIONS: dict[str, set[str]] = {
    # Orchestrator: read the job, update status, assign directly, delegate.
    "project_manager": {
        "get_job",
        "update_job_status",
        "assign_subcontractor",
        "get_schedule",
        "create_schedule",
        "update_schedule",
        "find_available_slots",
        "delegate_to_agent",
    },
    # Finds best-fit sub and assigns them.
    "matching": {
        "get_job",
        "search_subcontractors",
        "detect_conflicts",
        "assign_subcontractor",
        "get_schedule",
        "find_available_slots",
        "create_schedule",
    },
    # Sends one targeted message. That's it.
    "communication": {
        "get_job",
        "send_message",
    },
    # Scores risk, logs findings, updates status if at-risk.
    "risk": {
        "get_job",
        "get_weather_forecast",
        "calculate_risk_score",
        "get_active_risks",
        "create_risk_record",
        "update_job_status",
    },
    # Finds new slot, creates/updates schedule, notifies sub, re-assigns if needed.
    "rescheduling": {
        "get_job",
        "find_available_slots",
        "create_schedule",
        "update_schedule",
        "search_subcontractors",
        "assign_subcontractor",
        "update_job_status",
    },
    # Read-only predictor — no state mutations.
    "predictor": {
        "get_job",
        "get_weather_forecast",
        "calculate_risk_score",
        "get_active_risks",
        "get_schedule",
    },
}

_ALIASES: dict[str, str] = {}


class ToolRegistry:
    def __init__(
        self,
        db: AsyncSession,
        depth: int = 0,
        *,
        delegate_budget: DelegateBudget | None = None,
        specialist_max_iterations: int | None = None,
    ) -> None:
        self._db = db
        self._depth = depth
        self._delegate_budget = delegate_budget if delegate_budget is not None else DelegateBudget(settings.max_delegate_calls)
        self._specialist_max_iterations = (
            settings.max_specialist_iterations if specialist_max_iterations is None else specialist_max_iterations
        )
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
        child._delegate_budget = self._delegate_budget
        child._specialist_max_iterations = self._specialist_max_iterations
        child._tools = self._tools
        child._schemas = self._schemas
        return child
