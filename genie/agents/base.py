"""Base agent with shared agentic loop."""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from genie.config import settings
from genie.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    success: bool
    summary: str
    data: dict = field(default_factory=dict)
    tool_calls_made: list[dict] = field(default_factory=list)


class BaseAgent(ABC):
    """Abstract base for all Genie agents. Provides the tool-use agentic loop."""

    agent_name: str = "base"

    def __init__(self, db: AsyncSession, registry: ToolRegistry) -> None:
        self.db = db
        self.registry = registry
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt that defines this agent's role."""

    async def run(
        self,
        task: str,
        context: dict | None = None,
        *,
        max_iterations: int | None = None,
        event_callback: Callable | None = None,
    ) -> AgentResult:
        """Run the agent on a task.

        Each *iteration* is one Anthropic `messages.create` call. If Claude returns
        `tool_use`, tools run and their results are appended; the loop calls Claude again.
        When Claude returns `end_turn` (no more tools), the loop stops — so actual
        iterations are often fewer than the cap.
        """
        context = context or {}
        cap = settings.max_agent_iterations if max_iterations is None else max_iterations
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": self._build_user_message(task, context)}
        ]

        tool_schemas = self.registry.get_schemas_for_agent(self.agent_name)
        tool_calls_log: list[dict] = []
        final_text = ""

        async def _emit(event: dict) -> None:
            if event_callback is not None:
                await event_callback(event)

        await _emit({"type": "agent_start", "agent": self.agent_name, "task": task[:120]})

        for iteration in range(cap):
            logger.info("[%s] Iteration %d — sending to Claude", self.agent_name, iteration + 1)

            response = await self.client.messages.create(
                model=settings.claude_model,
                max_tokens=settings.claude_max_tokens,
                temperature=0,
                system=self.system_prompt,
                tools=tool_schemas,  # type: ignore[arg-type]
                messages=messages,
            )

            # Collect any text blocks
            text_blocks = [b.text for b in response.content if b.type == "text"]
            if text_blocks:
                final_text = "\n".join(text_blocks)
                await _emit({"type": "thinking", "agent": self.agent_name, "text": final_text[:200]})

            # If Claude is done, break
            if response.stop_reason == "end_turn":
                break

            # Process tool use blocks
            if response.stop_reason == "tool_use":
                # Append assistant message with all content blocks
                messages.append({"role": "assistant", "content": response.content})

                # Execute all tool calls and collect results
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tool_input = block.input
                    logger.info("[%s] Calling tool: %s(%s)", self.agent_name, tool_name, list(tool_input.keys()))

                    await _emit({"type": "tool_call", "agent": self.agent_name, "tool": tool_name, "input_keys": list(tool_input.keys())})

                    result = await self.registry.call(tool_name, tool_input)
                    tool_calls_log.append({"tool": tool_name, "input": tool_input, "result": result})

                    result_summary = str(result)[:120]
                    await _emit({"type": "tool_result", "agent": self.agent_name, "tool": tool_name, "summary": result_summary})

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": self._truncate_tool_result(result),
                    })

                messages.append({"role": "user", "content": tool_results})
            else:
                # Unexpected stop reason
                break

        await _emit({"type": "agent_done", "agent": self.agent_name, "summary": (final_text or f"{self.agent_name} completed.")[:200]})

        await self._log_action(task, context, final_text, tool_calls_log)

        return AgentResult(
            success=True,
            summary=final_text or f"{self.agent_name} completed task.",
            tool_calls_made=tool_calls_log,
        )

    def _truncate_tool_result(self, result: Any) -> str:
        text = str(result)
        limit = settings.tool_result_max_chars
        if len(text) <= limit:
            return text
        return text[: limit - 40] + "\n… [truncated — tool output exceeded limit]"

    def _build_user_message(self, task: str, context: dict) -> str:
        ctx_str = "\n".join(f"  {k}: {v}" for k, v in context.items()) if context else "  (none)"
        return (
            f"Task: {task}\n\nContext:\n{ctx_str}\n\n"
            "Efficiency: use the minimum number of tool rounds. Follow your playbook in order; "
            "do not make exploratory or duplicate tool calls."
        )

    async def _log_action(
        self,
        task: str,
        context: dict,
        output: str,
        tool_calls: list[dict],
    ) -> None:
        from genie.db.models import AgentLog

        log = AgentLog(
            id=str(uuid.uuid4()),
            agent_name=self.agent_name,
            job_id=context.get("job_id"),
            action=task[:200],
            input_summary=str(context)[:500],
            output_summary=output[:500] if output else None,
            tool_calls=[{"tool": tc["tool"], "input_keys": list(tc["input"].keys())} for tc in tool_calls],
            timestamp=datetime.utcnow(),
        )
        self.db.add(log)
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
