from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from app.adapters.base import BaseAgentAdapter
from app.core.agent_router import AgentRouter


class ChatService:
    def __init__(self) -> None:
        self.router = AgentRouter()

    def send_message(
        self,
        *,
        workspace_root: str,
        session: dict[str, Any],
        user_message: str,
        task_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        adapter = self.router.get_adapter(session["agent_id"])
        prompt = self._build_prompt(session=session, user_message=user_message, task_context=task_context)
        if session["agent_id"] == "codex":
            return self._run_codex(adapter, workspace_root=workspace_root, prompt=prompt)
        if session["agent_id"] == "claude-code":
            return self._run_claude(adapter, workspace_root=workspace_root, prompt=prompt)
        if session["agent_id"] == "gemini-cli":
            return self._run_gemini(adapter, workspace_root=workspace_root, prompt=prompt)
        raise KeyError(f"Unsupported chat agent: {session['agent_id']}")

    def _build_prompt(self, *, session: dict[str, Any], user_message: str, task_context: dict[str, Any] | None) -> str:
        history = session.get("messages", [])[-12:]
        lines = [
            "You are inside the ESAA Supervisor project chat.",
            "Respond normally in prose or code fences.",
            "Do not emit ESAA workflow JSON unless the user explicitly asks for it.",
            "You may inspect and modify the current workspace when needed.",
        ]
        if session.get("mode") == "task" and task_context:
            lines.extend(
                [
                    "",
                    "Task-linked context:",
                    f"- task_id: {task_context.get('task_id')}",
                    f"- title: {task_context.get('title')}",
                    f"- status: {task_context.get('status')}",
                    f"- task_kind: {task_context.get('task_kind')}",
                    f"- description: {task_context.get('description')}",
                    f"- roadmap_id: {session.get('roadmap_id')}",
                ]
            )
        if history:
            lines.append("")
            lines.append("Conversation so far:")
            for message in history:
                role = message.get("role", "user").upper()
                lines.append(f"{role}: {message.get('content', '')}")
        lines.append("")
        lines.append(f"USER: {user_message}")
        return "\n".join(lines)

    def _run_codex(self, adapter: BaseAgentAdapter, *, workspace_root: str, prompt: str) -> dict[str, Any]:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as handle:
            output_path = handle.name
        command = adapter._prepare_command([
            adapter.resolve_command(),
            "exec",
            "--skip-git-repo-check",
            "--color",
            "never",
            "--sandbox",
            "workspace-write",
            "--output-last-message",
            output_path,
            "-",
        ])
        return self._run_subprocess(
            command=command,
            cwd=workspace_root,
            stdin_payload=prompt,
            response_extractor=lambda stdout, stderr: self._extract_codex_response(output_path, stdout, stderr),
            token_extractor=lambda stdout, stderr: self._extract_codex_tokens(f"{stdout}\n{stderr}"),
        )

    def _run_claude(self, adapter: BaseAgentAdapter, *, workspace_root: str, prompt: str) -> dict[str, Any]:
        command = adapter._prepare_command([
            adapter.resolve_command(),
            "-p",
            "--output-format",
            "json",
            "--permission-mode",
            "bypassPermissions",
        ])
        return self._run_subprocess(
            command=command,
            cwd=workspace_root,
            stdin_payload=prompt,
            response_extractor=self._extract_claude_response,
            token_extractor=self._extract_claude_tokens,
        )

    def _run_gemini(self, adapter: BaseAgentAdapter, *, workspace_root: str, prompt: str) -> dict[str, Any]:
        command = adapter._prepare_command([
            adapter.resolve_command(),
            "-p",
            "",
            "--approval-mode",
            "yolo",
            "--output-format",
            "json",
        ])
        return self._run_subprocess(
            command=command,
            cwd=workspace_root,
            stdin_payload=prompt,
            response_extractor=self._extract_gemini_response,
            token_extractor=self._extract_gemini_tokens,
        )

    def _run_subprocess(
        self,
        *,
        command: list[str],
        cwd: str,
        stdin_payload: str,
        response_extractor,
        token_extractor,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        completed = subprocess.run(
            command,
            cwd=cwd,
            input=stdin_payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600,
            check=False,
            env=os.environ.copy(),
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        duration_ms = int((time.perf_counter() - started) * 1000)
        return {
            "content": response_extractor(stdout, stderr),
            "metadata": {
                "exit_code": completed.returncode,
                "duration_ms": duration_ms,
                "stdout": stdout,
                "stderr": stderr,
                "command": command,
                "token_usage": token_extractor(stdout, stderr),
            },
        }

    @staticmethod
    def _extract_codex_response(output_path: str, stdout: str, stderr: str) -> str:
        try:
            content = Path(output_path).read_text(encoding="utf-8").strip()
        finally:
            Path(output_path).unlink(missing_ok=True)
        if content:
            return content
        raw = f"{stdout}\n{stderr}".strip()
        if not raw:
            return ""
        return raw

    @staticmethod
    def _extract_codex_tokens(raw_output: str) -> dict[str, Any] | None:
        match = re.search(r"tokens used\s*([\d\.,]+)", raw_output, re.IGNORECASE)
        if not match:
            return None
        numeric = match.group(1).replace(".", "").replace(",", "")
        if not numeric.isdigit():
            return None
        return {"total": int(numeric), "models": {}}

    @staticmethod
    def _extract_claude_response(stdout: str, stderr: str) -> str:
        try:
            wrapper = json.loads(stdout)
        except json.JSONDecodeError:
            return stdout.strip() or stderr.strip()
        if isinstance(wrapper, dict):
            result = wrapper.get("result")
            if isinstance(result, str):
                return result.strip()
        return stdout.strip() or stderr.strip()

    @staticmethod
    def _extract_claude_tokens(stdout: str, stderr: str) -> dict[str, Any] | None:
        try:
            wrapper = json.loads(stdout)
        except json.JSONDecodeError:
            return None
        if not isinstance(wrapper, dict):
            return None
        usage = wrapper.get("usage")
        model_usage = wrapper.get("modelUsage")
        total_cost_usd = wrapper.get("total_cost_usd")
        token_usage: dict[str, Any] = {}
        if isinstance(usage, dict):
            token_usage["input"] = usage.get("input_tokens")
            token_usage["output"] = usage.get("output_tokens")
            token_usage["cache_creation_input"] = usage.get("cache_creation_input_tokens")
            token_usage["cache_read_input"] = usage.get("cache_read_input_tokens")
            token_usage["total"] = sum(
                value for value in [
                    usage.get("input_tokens"),
                    usage.get("output_tokens"),
                    usage.get("cache_creation_input_tokens"),
                    usage.get("cache_read_input_tokens"),
                ]
                if isinstance(value, int)
            )
        if isinstance(model_usage, dict):
            token_usage["models"] = model_usage
        if isinstance(total_cost_usd, (int, float)):
            token_usage["total_cost_usd"] = total_cost_usd
        return token_usage or None

    @staticmethod
    def _extract_gemini_response(stdout: str, stderr: str) -> str:
        try:
            wrapper = json.loads(stdout)
        except json.JSONDecodeError:
            return stdout.strip() or stderr.strip()
        if isinstance(wrapper, dict):
            response = wrapper.get("response")
            if isinstance(response, str):
                return response.strip()
        return stdout.strip() or stderr.strip()

    @staticmethod
    def _extract_gemini_tokens(stdout: str, stderr: str) -> dict[str, Any] | None:
        try:
            wrapper = json.loads(stdout)
        except json.JSONDecodeError:
            return None
        if not isinstance(wrapper, dict):
            return None
        stats = wrapper.get("stats")
        if not isinstance(stats, dict):
            return None
        models = stats.get("models", {})
        flattened: dict[str, Any] = {}
        if isinstance(models, dict):
            for model_name, payload in models.items():
                if isinstance(payload, dict) and isinstance(payload.get("tokens"), dict):
                    flattened[model_name] = payload["tokens"]
        total = sum(
            value.get("total", 0)
            for value in flattened.values()
            if isinstance(value, dict)
        )
        return {
            "total": total or None,
            "stats": stats,
            "models": flattened,
        }
