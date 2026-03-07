from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


AgentAction = Literal["claim", "complete", "issue.report"]


class VerificationCheck(BaseModel):
    id: str | None = None
    status: Literal["pass", "fail"] | None = None
    title: str | None = None
    evidence: str | None = None


class FileUpdate(BaseModel):
    path: str
    content: str


class AgentPayload(BaseModel):
    task_id: str
    verification_checks: list[VerificationCheck] = Field(default_factory=list)
    file_updates: list[FileUpdate] = Field(default_factory=list)
    raw_event: dict[str, Any] | None = None
    error: str | None = None


class AgentMetadata(BaseModel):
    exit_code: int | None = None
    duration_ms: int
    raw_output: str
    stdout: str = ""
    stderr: str = ""
    command: list[str] = Field(default_factory=list)
    timed_out: bool = False


class AgentResult(BaseModel):
    action: AgentAction
    actor: str
    payload: AgentPayload
    metadata: AgentMetadata
