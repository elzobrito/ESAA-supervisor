from __future__ import annotations

import json
from typing import Any

from app.adapters.base import BaseAgentAdapter
from app.models.task_context import TaskContext


class GeminiAdapter(BaseAgentAdapter):
    actor = "gemini-cli"
    command_name = "gemini"

    def build_command(self, context: TaskContext, prompt: str) -> list[str]:
        return [
            self.resolve_command(),
            "-p",
            "",
            "--approval-mode",
            "yolo",
            "--output-format",
            "json",
        ]

    def build_stdin(self, context: TaskContext, prompt: str) -> str:
        return json.dumps({"prompt": prompt, "context": context.model_dump(mode="json")}, ensure_ascii=False)

    def _extract_result_payload(self, *, raw_output: str, stdout: str, stderr: str) -> dict | None:
        wrapper = self._extract_wrapper(stdout)
        if wrapper is not None:
            response = wrapper.get("response", "")
            if isinstance(response, str):
                return self._extract_result_json(response) or self._extract_result_json(raw_output)
        return self._extract_result_json(raw_output)

    def _extract_metadata_extras(self, *, raw_output: str, stdout: str, stderr: str) -> dict[str, Any]:
        wrapper = self._extract_wrapper(stdout)
        if not wrapper:
            return {}
        stats = wrapper.get("stats")
        if not isinstance(stats, dict):
            return {}
        return {
            "token_usage": {
                "stats": stats,
                "models": self._flatten_model_tokens(stats.get("models", {})),
            }
        }

    @staticmethod
    def _extract_wrapper(stdout: str) -> dict[str, Any] | None:
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    @staticmethod
    def _flatten_model_tokens(models: dict[str, Any]) -> dict[str, Any]:
        flattened: dict[str, Any] = {}
        for model_name, model_payload in models.items():
            if not isinstance(model_payload, dict):
                continue
            tokens = model_payload.get("tokens")
            if isinstance(tokens, dict):
                flattened[model_name] = tokens
        return flattened
