from __future__ import annotations

import json
from typing import Any

from app.adapters.base import BaseAgentAdapter
from app.models.task_context import TaskContext


class ClaudeAdapter(BaseAgentAdapter):
    actor = "claude-code"
    command_name = "claude"

    def build_command(self, context: TaskContext, prompt: str) -> list[str]:
        command = [
            self.resolve_command(),
            "-p",
            "--output-format",
            "json",
            "--permission-mode",
            "bypassPermissions",
        ]
        model_id = self.selected_model(context)
        if model_id:
            command.extend(["--model", model_id])
        reasoning_effort = self.selected_reasoning_effort(context)
        if reasoning_effort:
            command.extend(["--effort", reasoning_effort])
        return command

    def build_stdin(self, context: TaskContext, prompt: str) -> str:
        return json.dumps({"prompt": prompt, "context": context.model_dump(mode="json")}, ensure_ascii=False)

    def _extract_result_payload(self, *, raw_output: str, stdout: str, stderr: str) -> dict | None:
        wrapper = self._extract_wrapper(stdout)
        if wrapper is not None:
            result = wrapper.get("result", "")
            if isinstance(result, str):
                return self._extract_result_json(result) or self._extract_result_json(raw_output)
        return self._extract_result_json(raw_output)

    def _extract_metadata_extras(self, *, raw_output: str, stdout: str, stderr: str) -> dict[str, Any]:
        wrapper = self._extract_wrapper(stdout)
        if not wrapper:
            return {}
        usage = wrapper.get("usage")
        model_usage = wrapper.get("modelUsage")
        total_cost_usd = wrapper.get("total_cost_usd")
        token_usage: dict[str, Any] = {}
        if isinstance(usage, dict):
            token_usage["total"] = (
                (usage.get("input_tokens") or 0)
                + (usage.get("output_tokens") or 0)
                + (usage.get("cache_creation_input_tokens") or 0)
                + (usage.get("cache_read_input_tokens") or 0)
            )
            token_usage["input"] = usage.get("input_tokens")
            token_usage["output"] = usage.get("output_tokens")
            token_usage["cache_creation_input"] = usage.get("cache_creation_input_tokens")
            token_usage["cache_read_input"] = usage.get("cache_read_input_tokens")
        if isinstance(model_usage, dict):
            token_usage["models"] = model_usage
        if isinstance(total_cost_usd, (int, float)):
            token_usage["total_cost_usd"] = total_cost_usd
        return {"token_usage": token_usage} if token_usage else {}

    @staticmethod
    def _extract_wrapper(stdout: str) -> dict[str, Any] | None:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
