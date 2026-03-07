from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.agent_router import AgentRouter
from app.core.event_writer import EventWriter
from app.core.locks import ProjectLock
from app.core.log_stream import LogStreamer
from app.core.projector import Projector
from app.core.selector import TaskSelector
from app.models.run_state import RunDecisionEntry, RunExecutionMode, RunLogEntry, RunState, RunStatus
from app.models.task_context import ActiveLesson, TaskContext, TaskOutputs


class RunEngine:
    _active_runs: Dict[str, RunState] = {}
    _run_tasks: Dict[str, asyncio.Task] = {}
    _decision_events: Dict[str, asyncio.Event] = {}
    _decision_payloads: Dict[str, dict[str, Any]] = {}

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.agent_router = AgentRouter()

    async def start_run(
        self,
        task_id: str,
        agent_id: str,
        roadmap_id: str | None = None,
        execution_mode: RunExecutionMode = RunExecutionMode.MANUAL,
        roadmap_dir: str | None = None,
        roadmap: dict[str, Any] | None = None,
        lessons: list[dict[str, Any]] | None = None,
    ) -> RunState:
        run_id = str(uuid.uuid4())

        if not ProjectLock.acquire(self.project_id, run_id):
            raise asyncio.CancelledError(f"Project {self.project_id} is already locked")

        run_state = RunState(
            run_id=run_id,
            task_id=task_id,
            agent_id=agent_id,
            roadmap_id=roadmap_id,
            execution_mode=execution_mode,
            status=RunStatus.PREFLIGHT,
        )
        self._active_runs[run_id] = run_state
        self._decision_events[run_id] = asyncio.Event()
        self._decision_payloads.pop(run_id, None)

        self._run_tasks[run_id] = asyncio.create_task(
            self._execute(
                run_id,
                roadmap_dir=roadmap_dir,
                roadmap=roadmap or {},
                lessons=lessons or [],
            )
        )

        return run_state

    async def _execute(self, run_id: str, *, roadmap_dir: str | None, roadmap: dict[str, Any], lessons: list[dict[str, Any]]) -> None:
        run_state = self._active_runs[run_id]

        try:
            while True:
                self._log(run_id, "system", f"Starting preflight for task {run_state.task_id}...")
                await asyncio.sleep(0.1)
                self._ensure_not_cancelled(run_state)

                current_roadmap = self._load_runtime_roadmap(
                    roadmap_dir=roadmap_dir,
                    roadmap_id=run_state.roadmap_id,
                    fallback=roadmap,
                )
                task = self._find_task(current_roadmap, run_state.task_id) if current_roadmap else {
                    "task_id": run_state.task_id,
                    "task_kind": "impl",
                    "title": run_state.task_id,
                    "description": run_state.task_id,
                    "status": "todo",
                }
                if roadmap_dir:
                    self._claim_task(run_state, task=task, roadmap_dir=roadmap_dir)
                    current_roadmap = self._load_runtime_roadmap(
                        roadmap_dir=roadmap_dir,
                        roadmap_id=run_state.roadmap_id,
                        fallback=current_roadmap,
                    )
                    task = self._find_task(current_roadmap, run_state.task_id)
                self._ensure_not_cancelled(run_state)

                run_state.status = RunStatus.RUNNING
                self._log(run_id, "system", f"Invoking agent {run_state.agent_id}...")

                context = self._build_context(task=task, roadmap_id=run_state.roadmap_id, lessons=lessons, roadmap_dir=roadmap_dir)
                adapter = self.agent_router.get_adapter(run_state.agent_id)
                result = await asyncio.to_thread(adapter.run, context, self._build_prompt(context), self._log_callback(run_id))

                run_state.exit_code = result.metadata.exit_code
                run_state.agent_result = result.model_dump(mode="json")
                run_state.proposed_action = result.action
                run_state.available_actions = ["claim", "complete", "issue.report"]

                selected_action = await self._resolve_selected_action(run_id, run_state, result.action, result.actor)
                self._ensure_not_cancelled(run_state)
                if selected_action is None:
                    run_state.status = RunStatus.CANCELLED
                    run_state.error_message = "Agent proposal rejected by user"
                    run_state.awaiting_decision = False
                    run_state.ended_at = datetime.now()
                    self._log(run_id, "system", "Run stopped after manual rejection.")
                    return

                run_state.status = RunStatus.SYNCING
                run_state.awaiting_decision = False
                run_state.proposed_action = selected_action
                self._log(run_id, "system", f"Applying selected action '{selected_action}'...")

                if roadmap_dir:
                    self._apply_selected_action(
                        run_state=run_state,
                        selected_action=selected_action,
                        roadmap_dir=roadmap_dir,
                        result=result.model_dump(mode="json"),
                    )

                if selected_action == "complete" and run_state.task_id not in run_state.completed_task_ids:
                    run_state.completed_task_ids.append(run_state.task_id)

                if run_state.execution_mode != RunExecutionMode.CONTINUOUS:
                    break

                if run_state.stop_after_current:
                    self._log(run_id, "system", "Graceful stop requested. Continuous execution will stop after the current task.")
                    break

                next_task = self._select_next_task(
                    roadmap_dir=roadmap_dir,
                    roadmap_id=run_state.roadmap_id,
                    current_task_id=run_state.task_id,
                )
                if not next_task:
                    self._log(run_id, "system", "No further eligible tasks found. Continuous execution is complete.")
                    break

                run_state.task_id = next_task["task_id"]
                run_state.agent_result = None
                run_state.proposed_action = None
                run_state.available_actions = []
                run_state.exit_code = None
                run_state.error_message = None
                self._log(run_id, "system", f"Continuing automatically with next eligible task {run_state.task_id}.")

            run_state.status = RunStatus.DONE
            run_state.ended_at = datetime.now()
            self._log(run_id, "system", "Run completed successfully.")

        except asyncio.CancelledError:
            run_state.status = RunStatus.CANCELLED
            run_state.error_message = "Run cancelled by user request"
            run_state.awaiting_decision = False
            run_state.ended_at = datetime.now()
            self._log(run_id, "system", "Run cancelled before completion.")
        except Exception as exc:
            run_state.status = RunStatus.ERROR
            run_state.error_message = str(exc)
            run_state.awaiting_decision = False
            run_state.ended_at = datetime.now()
            self._log(run_id, "system", f"Run failed: {str(exc)}")
        finally:
            ProjectLock.release(self.project_id, run_id)
            self._run_tasks.pop(run_id, None)
            self._decision_events.pop(run_id, None)

    def _claim_task(self, run_state: RunState, *, task: dict[str, Any], roadmap_dir: str) -> None:
        if task.get("status") != "todo":
            return
        writer = EventWriter(roadmap_dir=roadmap_dir)
        claim_event = writer.append_event(
            actor=run_state.agent_id,
            action="claim",
            payload={
                "task_id": run_state.task_id,
                "prior_status": task.get("status", "todo"),
            },
        )
        Projector(roadmap_dir, roadmap_id=run_state.roadmap_id or "roadmap.json").sync_to_disk([claim_event])
        self._log(run_state.run_id, "system", f"Claim recorded for task {run_state.task_id}.")

    def _apply_selected_action(
        self,
        *,
        run_state: RunState,
        selected_action: str,
        roadmap_dir: str,
        result: dict[str, Any],
    ) -> None:
        if selected_action not in {"claim", "complete", "issue.report"}:
            raise ValueError(f"Unsupported selected action: {selected_action}")

        payload = result.get("payload", {})
        execution_metadata = self._build_execution_metadata(run_state=run_state, result=result)
        writer = EventWriter(roadmap_dir=roadmap_dir)
        events: list[dict[str, Any]] = []

        if selected_action == "claim":
            return

        if selected_action == "complete":
            verification_checks = payload.get("verification_checks", [])
            complete_payload: dict[str, Any] = {
                "task_id": run_state.task_id,
                "verification": {"checks": verification_checks},
            }
            if execution_metadata:
                complete_payload["agent_execution"] = execution_metadata
            if payload.get("error"):
                complete_payload["fixes"] = payload["error"]
            events.extend(
                [
                    writer.build_event(
                        actor=run_state.agent_id,
                        action="complete",
                        payload=complete_payload,
                    ),
                    writer.build_event(
                        actor="orchestrator",
                        action="review",
                        payload={"task_id": run_state.task_id, "decision": "approve"},
                    ),
                ]
            )
        elif selected_action == "issue.report":
            issue_id = f"ISS-RUN-{run_state.run_id[:8].upper()}"
            events.append(
                writer.build_event(
                    actor=run_state.agent_id,
                    action="issue.report",
                    payload={
                        "issue_id": issue_id,
                        "task_id": run_state.task_id,
                        "severity": "medium",
                        "title": f"Agent reported issue while executing {run_state.task_id}",
                        "evidence": payload.get("error") or "Agent requested issue reporting from manual review flow.",
                        "affected": {"task_id": run_state.task_id},
                        **({"agent_execution": execution_metadata} if execution_metadata else {}),
                    },
                )
            )

        written = writer.append_events(events)
        if written:
            Projector(roadmap_dir, roadmap_id=run_state.roadmap_id or "roadmap.json").sync_to_disk(written)
            self._log(run_state.run_id, "system", f"Persisted {len(written)} event(s) for action '{selected_action}'.")

    async def _resolve_selected_action(
        self,
        run_id: str,
        run_state: RunState,
        proposed_action: str,
        actor: str,
    ) -> str | None:
        if run_state.execution_mode == RunExecutionMode.CONTINUOUS:
            run_state.awaiting_decision = False
            run_state.status = RunStatus.RUNNING
            run_state.decision_history.append(
                RunDecisionEntry(
                    stage="proposal",
                    proposed_action=proposed_action,
                    actor=actor,
                    notes="Agent returned a proposal and continuous mode auto-approved continuation.",
                )
            )
            run_state.decision_history.append(
                RunDecisionEntry(
                    stage="decision",
                    proposed_action=proposed_action,
                    selected_action=proposed_action,
                    decision="apply",
                    actor="system",
                    notes="Continuous mode applied the proposed action automatically.",
                )
            )
            self._log(run_id, "system", f"Agent proposed action '{proposed_action}'. Continuous mode auto-approved continuation.")
            return proposed_action

        run_state.awaiting_decision = True
        run_state.status = RunStatus.WAITING_INPUT
        run_state.decision_history.append(
            RunDecisionEntry(
                stage="proposal",
                proposed_action=proposed_action,
                actor=actor,
                notes="Agent returned a proposal and execution is paused for manual review.",
            )
        )
        self._log(run_id, "system", f"Agent proposed action '{proposed_action}'. Awaiting manual decision.")

        await self._wait_for_decision(run_id, run_state)
        self._ensure_not_cancelled(run_state)

        decision = self._decision_payloads.pop(run_id, {"decision": "reject"})
        if decision.get("decision") != "apply":
            run_state.decision_history.append(
                RunDecisionEntry(
                    stage="decision",
                    proposed_action=proposed_action,
                    decision="reject",
                    actor="user",
                    notes="Manual reviewer rejected the proposal.",
                )
            )
            return None

        selected_action = decision.get("selected_action") or proposed_action
        run_state.decision_history.append(
            RunDecisionEntry(
                stage="decision",
                proposed_action=proposed_action,
                selected_action=selected_action,
                decision="apply",
                actor="user",
                notes="Manual reviewer approved continuation with the selected action.",
            )
        )
        return selected_action

    @staticmethod
    def _load_json(path: str) -> dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_runtime_roadmap(
        self,
        *,
        roadmap_dir: str | None,
        roadmap_id: str | None,
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        if not roadmap_dir:
            return fallback
        roadmap_path = os.path.join(roadmap_dir, roadmap_id or "roadmap.json")
        if not os.path.exists(roadmap_path):
            return fallback
        return self._load_json(roadmap_path)

    def _load_open_issues(self, roadmap_dir: str | None) -> list[dict[str, Any]]:
        if not roadmap_dir:
            return []
        issues_path = os.path.join(roadmap_dir, "issues.json")
        if not os.path.exists(issues_path):
            return []
        payload = self._load_json(issues_path)
        if isinstance(payload, dict):
            issues = payload.get("issues", [])
        else:
            issues = payload
        return [issue for issue in issues if issue.get("status") == "open"]

    def _select_next_task(
        self,
        *,
        roadmap_dir: str | None,
        roadmap_id: str | None,
        current_task_id: str,
    ) -> Optional[dict[str, Any]]:
        if not roadmap_dir:
            return None
        roadmap = self._load_runtime_roadmap(roadmap_dir=roadmap_dir, roadmap_id=roadmap_id, fallback={})
        selector = TaskSelector(roadmap, self._load_open_issues(roadmap_dir))
        next_task = selector.select_next_task()
        if next_task and next_task.get("task_id") == current_task_id:
            return None
        return next_task

    def _build_context(
        self,
        *,
        task: dict[str, Any],
        roadmap_id: str | None,
        lessons: list[dict[str, Any]],
        roadmap_dir: str | None,
    ) -> TaskContext:
        active_lessons = [
            ActiveLesson(id=lesson.get("lesson_id", ""), content=lesson.get("rule", ""))
            for lesson in lessons
            if lesson.get("status", "active") == "active"
        ]
        raw_outputs = task.get("outputs", [])
        output_files = raw_outputs.get("files", []) if isinstance(raw_outputs, dict) else raw_outputs
        return TaskContext(
            task_id=task["task_id"],
            task_kind=task.get("task_kind", "impl"),
            description=task.get("description", task.get("title", "")),
            targets=task.get("target_paths", []),
            outputs=TaskOutputs(files=output_files),
            prior_status=task.get("status", "todo"),
            active_lessons=active_lessons,
            metadata={
                "workspace_root": self._workspace_root_from_roadmap_dir(roadmap_dir),
                "roadmap_id": roadmap_id or "roadmap.json",
                "title": task.get("title", ""),
            },
        )

    @staticmethod
    def _build_execution_metadata(*, run_state: RunState, result: dict[str, Any]) -> dict[str, Any]:
        metadata = result.get("metadata", {})
        if not isinstance(metadata, dict):
            return {}

        execution: dict[str, Any] = {
            "run_id": run_state.run_id,
            "agent_id": run_state.agent_id,
            "duration_ms": metadata.get("duration_ms"),
            "exit_code": metadata.get("exit_code"),
            "timed_out": metadata.get("timed_out", False),
        }
        token_usage = metadata.get("token_usage")
        if isinstance(token_usage, dict) and token_usage:
            execution["token_usage"] = token_usage
        return {key: value for key, value in execution.items() if value is not None and value != {}}

    @staticmethod
    def _load_init_prompt(workspace_root: str | None) -> str:
        if not workspace_root:
            return ""
        init_path = os.path.join(workspace_root, ".roadmap", "init.yaml")
        if not os.path.exists(init_path):
            return ""
        with open(init_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    @classmethod
    def _build_prompt(cls, context: TaskContext) -> str:
        workspace_root = context.metadata.get("workspace_root")
        init_prompt = cls._load_init_prompt(workspace_root)
        base_prompt = (
            "You are executing an ESAA task. "
            "Return a single JSON object on the last line with action in "
            "['claim','complete','issue.report'] and payload.task_id set correctly. "
            "Do not return prose after the final JSON line. "
            f"Task: {context.task_id}. Description: {context.description}"
        )
        if not init_prompt:
            return base_prompt
        return f"{init_prompt}\n\n# EXECUTION ENVELOPE\n{base_prompt}"

    @staticmethod
    def _find_task(roadmap: dict[str, Any], task_id: str) -> dict[str, Any]:
        for task in roadmap.get("tasks", []):
            if task.get("task_id") == task_id:
                return task
        raise ValueError(f"Task not found in roadmap: {task_id}")

    @staticmethod
    def _workspace_root_from_roadmap_dir(roadmap_dir: str | None) -> str | None:
        if not roadmap_dir:
            return None
        return os.path.dirname(roadmap_dir)

    def _log(self, run_id: str, source: str, content: str) -> None:
        entry = RunLogEntry(source=source, content=content)
        run_state = self._active_runs[run_id]
        run_state.logs.append(entry)
        LogStreamer.add_log(run_id, entry)

    def _log_callback(self, run_id: str):
        def emit(source: str, content: str) -> None:
            self._log(run_id, source, content)
        return emit

    async def _wait_for_decision(self, run_id: str, run_state: RunState) -> None:
        event = self._decision_events[run_id]
        while not event.is_set():
            self._ensure_not_cancelled(run_state)
            try:
                await asyncio.wait_for(event.wait(), timeout=0.25)
            except asyncio.TimeoutError:
                continue

    @classmethod
    def submit_decision(cls, run_id: str, decision: str, selected_action: str | None = None) -> Optional[RunState]:
        run_state = cls._active_runs.get(run_id)
        event = cls._decision_events.get(run_id)
        if not run_state or not event:
            return None
        cls._decision_payloads[run_id] = {
            "decision": decision,
            "selected_action": selected_action,
        }
        event.set()
        return run_state

    @classmethod
    def get_run_state(cls, run_id: str) -> Optional[RunState]:
        return cls._active_runs.get(run_id)

    @classmethod
    def request_stop_after_current(cls, run_id: str) -> Optional[RunState]:
        run_state = cls._active_runs.get(run_id)
        if not run_state:
            return None
        run_state.stop_after_current = True
        run_state.decision_history.append(
            RunDecisionEntry(
                stage="control",
                decision="stop_after_current",
                actor="user",
                notes="Operator requested a graceful stop after the current task finishes.",
            )
        )
        return run_state

    @classmethod
    def cancel_run(cls, project_id: str, run_id: str) -> bool:
        run_state = cls._active_runs.get(run_id)
        task = cls._run_tasks.get(run_id)
        if not run_state or not task:
            return False

        if run_state.status in (RunStatus.DONE, RunStatus.ERROR, RunStatus.CANCELLED):
            return False

        run_state.status = RunStatus.CANCELLING
        decision_event = cls._decision_events.get(run_id)
        if decision_event:
            decision_event.set()
        ProjectLock.release(project_id, run_id)
        task.cancel()
        return True

    @staticmethod
    def _ensure_not_cancelled(run_state: RunState) -> None:
        if run_state.status == RunStatus.CANCELLING:
            raise asyncio.CancelledError
