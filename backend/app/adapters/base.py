from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from typing import Callable

from app.models.agent_result import AgentMetadata, AgentPayload, AgentResult, FileUpdate, VerificationCheck
from app.models.task_context import TaskContext


LogCallback = Callable[[str, str], None]


class BaseAgentAdapter(ABC):
    actor: str
    command_name: str

    def __init__(self, *, timeout_seconds: int = 600, env: dict[str, str] | None = None):
        self.timeout_seconds = timeout_seconds
        self.env = env or {}

    def is_available(self) -> bool:
        resolved = self.resolve_command()
        return bool(resolved and (os.path.isabs(resolved) or shutil.which(resolved)))

    def resolve_command(self) -> str:
        env_name = f"ESAA_{self.actor.upper().replace('-', '_')}_COMMAND"
        configured = self.env.get(env_name) or os.getenv(env_name) or self.command_name
        return shutil.which(configured) or configured

    @abstractmethod
    def build_command(self, context: TaskContext, prompt: str) -> list[str]:
        raise NotImplementedError

    def build_stdin(self, context: TaskContext, prompt: str) -> str | None:
        return None

    def run(self, context: TaskContext, prompt: str, log_callback: LogCallback | None = None) -> AgentResult:
        started = time.perf_counter()
        command = self._prepare_command(self.build_command(context, prompt))
        stdin_payload = self.build_stdin(context, prompt)
        merged_env = os.environ.copy()
        merged_env.update(self.env)

        try:
            completed = subprocess.run(
                command,
                cwd=context.metadata.get("workspace_root"),
                input=stdin_payload,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.timeout_seconds,
                env=merged_env,
                check=False,
            )
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            self._emit_logs(stdout, stderr, log_callback)
            duration_ms = int((time.perf_counter() - started) * 1000)
            metadata_extras = self._extract_metadata_extras(raw_output=self._merge_output(stdout, stderr), stdout=stdout, stderr=stderr)
            return self._normalize_result(
                context=context,
                exit_code=completed.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                command=command,
                metadata_extras=metadata_extras,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            self._emit_logs(stdout, stderr, log_callback)
            duration_ms = int((time.perf_counter() - started) * 1000)
            return self._issue_result(
                context=context,
                error=f"Agent timed out after {self.timeout_seconds}s",
                exit_code=None,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                command=command,
                timed_out=True,
                metadata_extras=self._extract_metadata_extras(raw_output=self._merge_output(stdout, stderr), stdout=stdout, stderr=stderr),
            )
        except FileNotFoundError:
            duration_ms = int((time.perf_counter() - started) * 1000)
            return self._issue_result(
                context=context,
                error=f"Agent command not found: {command[0]}",
                exit_code=None,
                stdout="",
                stderr="",
                duration_ms=duration_ms,
                command=command,
                metadata_extras={},
            )

    @staticmethod
    def _prepare_command(command: list[str]) -> list[str]:
        if not command:
            return command
        executable = command[0]
        if os.name == "nt" and executable.lower().endswith((".cmd", ".bat")):
            return ["cmd", "/c", executable, *command[1:]]
        return command

    def _normalize_result(
        self,
        *,
        context: TaskContext,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_ms: int,
        command: list[str],
        metadata_extras: dict | None = None,
    ) -> AgentResult:
        raw_output = self._merge_output(stdout, stderr)
        parsed = self._extract_result_payload(raw_output=raw_output, stdout=stdout, stderr=stderr)
        metadata_extras = metadata_extras or {}
        if exit_code != 0 and parsed is None:
            return self._issue_result(
                context=context,
                error=f"{self.actor} exited with code {exit_code}",
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                command=command,
                metadata_extras=metadata_extras,
            )

        if parsed is None:
            return self._issue_result(
                context=context,
                error="Agent did not return valid JSON",
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                command=command,
                metadata_extras=metadata_extras,
            )

        payload = parsed.get("payload", {})
        verification_checks = [
            VerificationCheck.model_validate(item) for item in payload.get("verification_checks", [])
        ]
        file_updates = [FileUpdate.model_validate(item) for item in payload.get("file_updates", [])]

        return AgentResult(
            action=parsed["action"],
            actor=parsed.get("actor", self.actor),
            payload=AgentPayload(
                task_id=payload.get("task_id", context.task_id),
                verification_checks=verification_checks,
                file_updates=file_updates,
                raw_event=parsed,
            ),
            metadata=AgentMetadata(
                exit_code=exit_code,
                duration_ms=duration_ms,
                raw_output=raw_output,
                stdout=stdout,
                stderr=stderr,
                command=command,
                **metadata_extras,
            ),
        )

    def _issue_result(
        self,
        *,
        context: TaskContext,
        error: str,
        exit_code: int | None,
        stdout: str,
        stderr: str,
        duration_ms: int,
        command: list[str],
        timed_out: bool = False,
        metadata_extras: dict | None = None,
    ) -> AgentResult:
        return AgentResult(
            action="issue.report",
            actor=self.actor,
            payload=AgentPayload(task_id=context.task_id, error=error),
            metadata=AgentMetadata(
                exit_code=exit_code,
                duration_ms=duration_ms,
                raw_output=self._merge_output(stdout, stderr),
                stdout=stdout,
                stderr=stderr,
                command=command,
                timed_out=timed_out,
                **(metadata_extras or {}),
            ),
        )

    def _extract_result_payload(self, *, raw_output: str, stdout: str, stderr: str) -> dict | None:
        return self._extract_result_json(raw_output)

    def _extract_metadata_extras(self, *, raw_output: str, stdout: str, stderr: str) -> dict:
        return {}

    @staticmethod
    def _merge_output(stdout: str, stderr: str) -> str:
        if stdout and stderr:
            return f"{stdout.rstrip()}\n{stderr.rstrip()}"
        return stdout or stderr

    @staticmethod
    def _emit_logs(stdout: str, stderr: str, log_callback: LogCallback | None) -> None:
        if log_callback is None:
            return
        for line in stdout.splitlines():
            log_callback("stdout", line)
        for line in stderr.splitlines():
            log_callback("stderr", line)

    @staticmethod
    def _extract_result_json(raw_output: str) -> dict | None:
        lines = [line.strip() for line in raw_output.splitlines() if line.strip()]
        for line in reversed(lines):
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and "action" in parsed:
                return parsed
        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) and "action" in parsed else None
