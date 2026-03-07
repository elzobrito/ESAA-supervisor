from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ActiveLesson(BaseModel):
    id: str
    content: str


class TaskOutputs(BaseModel):
    files: list[str] = Field(default_factory=list)


class TaskContext(BaseModel):
    task_id: str
    task_kind: Literal["spec", "impl", "qa"]
    description: str
    targets: list[str] = Field(default_factory=list)
    outputs: TaskOutputs = Field(default_factory=TaskOutputs)
    prior_status: Literal["todo", "in_progress"]
    active_lessons: list[ActiveLesson] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
