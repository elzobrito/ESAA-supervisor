from __future__ import annotations

import json
import os
import re
import tempfile
from typing import Any

from app.adapters.base import BaseAgentAdapter
from app.models.task_context import TaskContext


class GeminiAdapter(BaseAgentAdapter):
    actor = "gemini-cli"
    command_name = "gemini"

    def build_command(self, context: TaskContext, prompt: str) -> list[str]:
        command = [
            self.resolve_command(),
            "-p",
            "",
            "--approval-mode",
            "yolo",
            "--output-format",
            "json",
        ]
        model_id = self.selected_model(context)
        if model_id:
            command.extend(["-m", model_id])
        return command

    def build_env(self, context: TaskContext, prompt: str) -> dict[str, str]:
        reasoning_effort = self.selected_reasoning_effort(context)
        model_id = self.selected_model(context)
        if not reasoning_effort or not model_id:
            return {}

        settings_path = self._write_settings_file(model_id=model_id, reasoning_effort=reasoning_effort)
        context.metadata["_gemini_settings_path"] = settings_path
        return {"GEMINI_CLI_SYSTEM_SETTINGS_PATH": settings_path}

    def cleanup_runtime(self, context: TaskContext, prompt: str) -> None:
        settings_path = context.metadata.pop("_gemini_settings_path", None)
        if isinstance(settings_path, str) and settings_path:
            try:
                os.remove(settings_path)
            except OSError:
                pass

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

    @classmethod
    def _write_settings_file(cls, *, model_id: str, reasoning_effort: str) -> str:
        fd, path = tempfile.mkstemp(prefix="esaa-gemini-settings-", suffix=".json")
        os.close(fd)
        payload = {
            "modelConfigs": {
                "customAliases": {
                    "esaa-run": {
                        "modelConfig": {
                            "model": model_id,
                            "generateContentConfig": {
                                "thinkingConfig": cls._thinking_config_for(model_id=model_id, reasoning_effort=reasoning_effort),
                            },
                        },
                    },
                },
            },
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return path

    @staticmethod
    def _thinking_config_for(*, model_id: str, reasoning_effort: str) -> dict[str, Any]:
        if model_id.startswith("gemini-3") or model_id == "auto-gemini-3":
            return {"thinkingLevel": reasoning_effort.upper()}

        budgets = {
            "low": 1024,
            "medium": 4096,
            "high": 8192,
        }
        return {"thinkingBudget": budgets.get(reasoning_effort, 4096)}
