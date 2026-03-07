from __future__ import annotations

import json
import re
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

    def sanitize_outputs(self, stdout: str, stderr: str) -> tuple[str, str]:
        return stdout, self._strip_known_windows_stderr_noise(stderr)

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

    @staticmethod
    def _strip_known_windows_stderr_noise(stderr: str) -> str:
        if not stderr.strip():
            return stderr

        filtered_lines: list[str] = []
        skip_stack = False

        for raw_line in stderr.splitlines():
            line = raw_line.strip()
            if not line:
                if not skip_stack:
                    filtered_lines.append(raw_line)
                continue

            if line in {
                "YOLO mode is enabled. All tool calls will be automatically approved.",
                "Loaded cached credentials.",
            }:
                continue

            if "conpty_console_list_agent.js:11" in line:
                skip_stack = True
                continue

            if skip_stack:
                if (
                    line == "var consoleProcessList = getConsoleProcessList(shellPid);"
                    or line == "^"
                    or line == "Error: AttachConsole failed"
                    or line.startswith("at ")
                    or re.fullmatch(r"Node\.js v\d+\.\d+\.\d+", line)
                ):
                    continue
                skip_stack = False

            filtered_lines.append(raw_line)

        return "\n".join(line for line in filtered_lines if line.strip())
