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
        return [
            self.resolve_command(),
            "exec",
            "--skip-git-repo-check",
            "--color",
            "never",
            "--sandbox",
            "workspace-write",
            "-",
        ]

    def build_stdin(self, context: TaskContext, prompt: str) -> str:
        return json.dumps({"prompt": prompt, "context": context.model_dump(mode="json")}, ensure_ascii=False)

    def _extract_metadata_extras(self, *, raw_output: str, stdout: str, stderr: str) -> dict[str, Any]:
        match = re.search(r"tokens used\s*([\d\.,]+)", raw_output, re.IGNORECASE)
        if not match:
            return {}
        numeric = match.group(1).replace(".", "").replace(",", "")
        if not numeric.isdigit():
            return {}
        total = int(numeric)
        return {
            "token_usage": {
                "total": total,
                "models": {},
            }
        }
