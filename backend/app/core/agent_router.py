from __future__ import annotations

from app.adapters.base import BaseAgentAdapter
from app.adapters.claude_adapter import ClaudeAdapter
from app.adapters.codex_adapter import CodexAdapter
from app.adapters.gemini_adapter import GeminiAdapter
from app.models.task_context import TaskContext


class AgentRouter:
    def __init__(self, adapters: dict[str, BaseAgentAdapter] | None = None):
        self.adapters = adapters or {
            "codex": CodexAdapter(),
            "claude-code": ClaudeAdapter(),
            "gemini-cli": GeminiAdapter(),
        }

    def get_adapter(self, agent_id: str) -> BaseAgentAdapter:
        if agent_id not in self.adapters:
            raise KeyError(f"Unknown agent adapter: {agent_id}")
        return self.adapters[agent_id]

    def choose_agent(self, context: TaskContext, preferred_runner: str | None = None) -> BaseAgentAdapter:
        candidates = self._candidate_order(context.task_kind, preferred_runner)
        for agent_id in candidates:
            adapter = self.adapters.get(agent_id)
            if adapter and adapter.is_available():
                return adapter
        for agent_id in candidates:
            adapter = self.adapters.get(agent_id)
            if adapter:
                return adapter
        raise RuntimeError(f"No adapter configured for task kind {context.task_kind}")

    @staticmethod
    def _candidate_order(task_kind: str, preferred_runner: str | None) -> list[str]:
        defaults = AgentRouter._defaults_for_kind(task_kind)
        if preferred_runner:
            return [preferred_runner, *[agent for agent in defaults if agent != preferred_runner]]
        return defaults

    @staticmethod
    def _defaults_for_kind(task_kind: str) -> list[str]:
        mapping = {
            "spec": ["claude-code", "gemini-cli", "codex"],
            "impl": ["claude-code", "codex", "gemini-cli"],
            "qa": ["gemini-cli", "claude-code", "codex"],
        }
        return mapping.get(task_kind, ["codex", "claude-code", "gemini-cli"])

    @classmethod
    def default_runner_for_kind(cls, task_kind: str) -> str:
        return cls._defaults_for_kind(task_kind)[0]
