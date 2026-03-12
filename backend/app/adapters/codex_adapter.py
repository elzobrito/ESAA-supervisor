from __future__ import annotations

import json
import re
from typing import Any

from app.adapters.base import BaseAgentAdapter
from app.models.task_context import TaskContext


class CodexAdapter(BaseAgentAdapter):
    actor = "codex"
    command_name = "codex"

    def build_command(self, context: TaskContext, prompt: str) -> list[str]:
        command = [self.resolve_command(), "exec"]
        resume_session_id = self._selected_resume_session_id(context)
        resume_last = self._selected_resume_last(context)
        if resume_session_id or resume_last:
            command.append("resume")
            command.append("--full-auto")
            command.append("--skip-git-repo-check")
            if resume_last:
                command.append("--last")
            if resume_session_id:
                command.append(resume_session_id)
            command.append("-")
        else:
            command.extend(
                [
                    "--skip-git-repo-check",
                    "--color",
                    "never",
                    "--sandbox",
                    "workspace-write",
                    "-",
                ]
            )
        model_id = self.selected_model(context)
        if model_id:
            command.extend(["-m", model_id])
        reasoning_effort = self.selected_reasoning_effort(context)
        if reasoning_effort:
            command.extend(["-c", f'reasoning_effort="{reasoning_effort}"'])
        return command

    def build_stdin(self, context: TaskContext, prompt: str) -> str:
        return json.dumps({"prompt": prompt, "context": context.model_dump(mode="json")}, ensure_ascii=False)

    def sanitize_outputs(self, stdout: str, stderr: str) -> tuple[str, str]:
        return stdout, self._strip_codex_transcript_noise(stderr)

    def _extract_metadata_extras(self, *, raw_output: str, stdout: str, stderr: str) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        match = re.search(r"tokens used\s*([\d\.,]+)", raw_output, re.IGNORECASE)
        if match:
            numeric = match.group(1).replace(".", "").replace(",", "")
            if numeric.isdigit():
                metadata["token_usage"] = {
                    "total": int(numeric),
                    "models": {},
                }

        session_match = re.search(r"session id:\s*([^\s]+)", raw_output, re.IGNORECASE)
        if session_match:
            metadata["codex_session_id"] = session_match.group(1).strip()

        return metadata

    @staticmethod
    def _selected_resume_session_id(context: TaskContext) -> str | None:
        session_id = context.metadata.get("codex_session_id")
        return session_id.strip() if isinstance(session_id, str) and session_id.strip() else None

    @staticmethod
    def _selected_resume_last(context: TaskContext) -> bool:
        return context.metadata.get("codex_resume_last") is True

    @staticmethod
    def _strip_codex_transcript_noise(stderr: str) -> str:
        if not stderr.strip():
            return stderr

        keep_prefixes = (
            "OpenAI Codex v",
            "--------",
            "workdir:",
            "model:",
            "provider:",
            "approval:",
            "sandbox:",
            "reasoning effort:",
            "reasoning summaries:",
            "session id:",
            "user",
            "mcp startup:",
            "warning:",
            "ERROR:",
            "tokens used",
        )
        filtered_lines: list[str] = []
        skipping_block = False

        for raw_line in stderr.splitlines():
            line = raw_line.strip()
            if line in {"codex", "exec"}:
                skipping_block = True
                continue

            if skipping_block:
                if line.startswith(keep_prefixes):
                    skipping_block = False
                else:
                    continue

            if (
                line.startswith('"C:\\Program Files\\PowerShell\\7\\pwsh.exe"')
                or line.startswith("succeeded in ")
                or line.startswith("exited ")
            ):
                continue

            filtered_lines.append(raw_line)

        return "\n".join(line for line in filtered_lines if line.strip())
