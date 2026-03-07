from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator


class RunCoordinator:
    MAX_ACTIVE_RUNS = 3
    _project_runs: dict[str, set[str]] = {}
    _run_projects: dict[str, str] = {}
    _busy_agents: dict[str, dict[str, str]] = {}
    _claimed_tasks: dict[str, dict[str, str]] = {}
    _admission_locks: dict[str, asyncio.Lock] = {}
    _event_locks: dict[str, asyncio.Lock] = {}

    @classmethod
    @asynccontextmanager
    async def admission(cls, project_id: str) -> AsyncIterator[None]:
        lock = cls._admission_locks.setdefault(project_id, asyncio.Lock())
        async with lock:
            yield

    @classmethod
    @asynccontextmanager
    async def event_write(cls, project_id: str) -> AsyncIterator[None]:
        lock = cls._event_locks.setdefault(project_id, asyncio.Lock())
        async with lock:
            yield

    @classmethod
    def ensure_capacity(cls, project_id: str, agent_id: str, task_id: str, *, run_id: str | None = None) -> None:
        project_runs = cls._project_runs.setdefault(project_id, set())
        busy_agents = cls._busy_agents.setdefault(project_id, {})
        claimed_tasks = cls._claimed_tasks.setdefault(project_id, {})

        if run_id is None and len(project_runs) >= cls.MAX_ACTIVE_RUNS:
            raise RuntimeError(f"Project {project_id} already has {cls.MAX_ACTIVE_RUNS} active runs")

        holder = busy_agents.get(agent_id)
        if holder and holder != run_id:
            raise RuntimeError(f"Agent {agent_id} is already executing another run")

        task_holder = claimed_tasks.get(task_id)
        if task_holder and task_holder != run_id:
            raise RuntimeError(f"Task {task_id} is already executing in another run")

    @classmethod
    def register_run(cls, project_id: str, run_id: str, agent_id: str, task_id: str) -> None:
        cls.ensure_capacity(project_id, agent_id, task_id)
        cls._project_runs.setdefault(project_id, set()).add(run_id)
        cls._run_projects[run_id] = project_id
        cls._busy_agents.setdefault(project_id, {})[agent_id] = run_id
        cls._claimed_tasks.setdefault(project_id, {})[task_id] = run_id

    @classmethod
    def claim_task(cls, project_id: str, run_id: str, task_id: str) -> None:
        cls._claimed_tasks.setdefault(project_id, {})
        holder = cls._claimed_tasks[project_id].get(task_id)
        if holder and holder != run_id:
            raise RuntimeError(f"Task {task_id} is already executing in another run")
        cls._claimed_tasks[project_id][task_id] = run_id

    @classmethod
    def release_task(cls, project_id: str, run_id: str, task_id: str | None) -> None:
        if not task_id:
            return
        project_claims = cls._claimed_tasks.get(project_id, {})
        if project_claims.get(task_id) == run_id:
            del project_claims[task_id]
        if not project_claims and project_id in cls._claimed_tasks:
            del cls._claimed_tasks[project_id]

    @classmethod
    def finish_run(cls, project_id: str, run_id: str, agent_id: str, task_id: str | None) -> None:
        cls.release_task(project_id, run_id, task_id)

        project_runs = cls._project_runs.get(project_id, set())
        project_runs.discard(run_id)
        if not project_runs and project_id in cls._project_runs:
            del cls._project_runs[project_id]

        busy_agents = cls._busy_agents.get(project_id, {})
        if busy_agents.get(agent_id) == run_id:
            del busy_agents[agent_id]
        if not busy_agents and project_id in cls._busy_agents:
            del cls._busy_agents[project_id]

        cls._run_projects.pop(run_id, None)

    @classmethod
    def active_run_ids(cls, project_id: str) -> list[str]:
        return sorted(cls._project_runs.get(project_id, set()))

    @classmethod
    def active_run_count(cls, project_id: str) -> int:
        return len(cls._project_runs.get(project_id, set()))

    @classmethod
    def remaining_slots(cls, project_id: str) -> int:
        return max(0, cls.MAX_ACTIVE_RUNS - cls.active_run_count(project_id))

    @classmethod
    def busy_agents(cls, project_id: str) -> list[str]:
        return sorted(cls._busy_agents.get(project_id, {}).keys())

    @classmethod
    def is_agent_busy(cls, project_id: str, agent_id: str) -> bool:
        return agent_id in cls._busy_agents.get(project_id, {})

    @classmethod
    def active_task_run_id(cls, project_id: str, task_id: str) -> str | None:
        return cls._claimed_tasks.get(project_id, {}).get(task_id)

    @classmethod
    def project_for_run(cls, run_id: str) -> str | None:
        return cls._run_projects.get(run_id)
