from __future__ import annotations

import json

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
            "text",
        ]

    def build_stdin(self, context: TaskContext, prompt: str) -> str:
        return json.dumps({"prompt": prompt, "context": context.model_dump(mode="json")}, ensure_ascii=False)
