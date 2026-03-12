import asyncio
import json
import threading
from pathlib import Path

import pytest

from app.core.log_stream import LogStreamer
from app.core.projector import Projector
from app.core.run_coordinator import RunCoordinator
from app.core.run_engine import RunEngine
from app.models.agent_result import AgentMetadata, AgentPayload, AgentResult
from app.models.run_state import RunExecutionMode, RunState, RunStatus


def setup_function() -> None:
    _reset_runtime_state()


def teardown_function() -> None:
    _reset_runtime_state()


def _reset_runtime_state() -> None:
    RunEngine._active_runs.clear()
    RunEngine._run_tasks.clear()
    RunEngine._decision_events.clear()
    RunEngine._decision_payloads.clear()
    RunEngine._agent_session_ids.clear()
    RunCoordinator._project_runs.clear()
    RunCoordinator._run_projects.clear()
    RunCoordinator._busy_agents.clear()
    RunCoordinator._claimed_tasks.clear()
    RunCoordinator._admission_locks.clear()
    RunCoordinator._event_locks.clear()
    LogStreamer._logs.clear()
    LogStreamer._queues.clear()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _seed_runtime_dir(tmp_path: Path, tasks: list[dict]) -> tuple[str, dict]:
    roadmap = {
        "meta": {
            "schema_version": "0.4.0",
            "esaa_version": "0.4.x",
            "immutable_done": True,
            "master_correlation_id": None,
            "run": {
                "run_id": None,
                "status": "initialized",
                "last_event_seq": 0,
                "projection_hash_sha256": "0" * 64,
                "verify_status": "ok",
            },
            "updated_at": "2026-03-07T00:00:00Z",
        },
        "project": {"name": "demo", "audit_scope": "test"},
        "tasks": tasks,
        "indexes": {
            "by_status": {"todo": len(tasks), "in_progress": 0, "review": 0, "done": 0},
            "by_kind": {"spec": 0, "impl": len(tasks), "qa": 0},
            "by_preferred_runner": {},
        },
    }
    issues = {
        "meta": {"schema_version": "0.4.0", "last_event_seq": 0, "updated_at": "2026-03-07T00:00:00Z"},
        "issues": [],
        "indexes": {"open_by_baseline": {}},
    }
    lessons = {
        "meta": {"schema_version": "0.4.0", "updated_at": "2026-03-07T00:00:00Z"},
        "lessons": [],
        "indexes": {"by_task_kind": {}, "by_enforcement_applies_to": {}},
    }
    _write_json(tmp_path / "roadmap.json", roadmap)
    roadmap["meta"]["run"]["projection_hash_sha256"] = Projector.compute_projection_hash(roadmap)
    _write_json(tmp_path / "roadmap.json", roadmap)
    _write_json(tmp_path / "issues.json", issues)
    _write_json(tmp_path / "lessons.json", lessons)
    (tmp_path / "activity.jsonl").write_text("", encoding="utf-8")
    return str(tmp_path), roadmap


def _task(
    task_id: str,
    *,
    runner: str = "gemini-cli",
    status: str = "todo",
    depends_on: list[str] | None = None,
) -> dict:
    return {
        "task_id": task_id,
        "task_kind": "impl",
        "title": task_id,
        "description": f"desc {task_id}",
        "status": status,
        "depends_on": depends_on or [],
        "targets": [],
        "outputs": {"files": []},
        "immutability": {"done_is_immutable": True},
        "required_verification": [],
        "planning": {
            "preferred_runner": runner,
        },
    }


class _Adapter:
    def __init__(self, actor: str, *, action: str = "complete", gate: threading.Event | None = None):
        self.actor = actor
        self.action = action
        self.gate = gate

    def run(self, context, prompt, log_callback=None):
        if self.gate is not None:
            self.gate.wait(timeout=2)
        if log_callback is not None:
            log_callback("stdout", f"{self.actor} executed {context.task_id}")
        payload = AgentPayload(task_id=context.task_id)
        if self.action == "issue.report":
            payload = AgentPayload(task_id=context.task_id, error="simulated issue")
        return AgentResult(
            action=self.action,
            actor=self.actor,
            payload=payload,
            metadata=AgentMetadata(
                exit_code=0,
                duration_ms=1,
                raw_output=json.dumps({"action": self.action}),
                stdout="",
                stderr="",
                command=[self.actor],
            ),
        )


class _Router:
    def __init__(self, adapters: dict[str, _Adapter]):
        self.adapters = adapters

    def get_adapter(self, agent_id: str):
        return self.adapters[agent_id]

    @staticmethod
    def default_runner_for_kind(task_kind: str) -> str:
        return {
            "spec": "claude-code",
            "impl": "codex",
            "qa": "gemini-cli",
        }.get(task_kind, "codex")


def test_run_waits_for_manual_decision_before_finishing(tmp_path: Path) -> None:
    async def scenario() -> None:
        roadmap_dir, roadmap = _seed_runtime_dir(tmp_path, [_task("TASK-1", runner="gemini-cli")])
        engine = RunEngine("project-manual")
        engine.agent_router = _Router({"gemini-cli": _Adapter("gemini-cli", action="issue.report")})

        run = await engine.start_run("TASK-1", "gemini-cli", roadmap_dir=roadmap_dir, roadmap=roadmap)

        for _ in range(40):
            if run.status == RunStatus.WAITING_INPUT:
                break
            await asyncio.sleep(0.05)

        assert run.status == RunStatus.WAITING_INPUT
        assert run.awaiting_decision is True
        assert run.proposed_action == "issue.report"

        RunEngine.submit_decision(run.run_id, "reject")

        for _ in range(40):
            if run.status in (RunStatus.CANCELLED, RunStatus.DONE, RunStatus.ERROR):
                break
            await asyncio.sleep(0.05)

        assert run.status == RunStatus.CANCELLED
        assert run.ended_at is not None
        assert run.decision_history[-1].decision == "reject"

    asyncio.run(scenario())


def test_continuous_run_auto_applies_and_moves_to_next_task(tmp_path: Path) -> None:
    async def scenario() -> None:
        tasks = [
            _task("TASK-1", runner="gemini-cli"),
            _task("TASK-2", runner="gemini-cli", depends_on=["TASK-1"]),
        ]
        roadmap_dir, roadmap = _seed_runtime_dir(tmp_path, tasks)
        engine = RunEngine("project-continuous")
        engine.agent_router = _Router({"gemini-cli": _Adapter("gemini-cli", action="complete")})

        run = await engine.start_run(
            "TASK-1",
            None,
            execution_mode=RunExecutionMode.CONTINUOUS,
            roadmap_dir=roadmap_dir,
            roadmap=roadmap,
        )

        for _ in range(80):
            if run.status in (RunStatus.DONE, RunStatus.ERROR, RunStatus.CANCELLED):
                break
            await asyncio.sleep(0.05)

        assert run.status == RunStatus.DONE
        assert run.awaiting_decision is False
        assert run.completed_task_ids == ["TASK-1", "TASK-2"]
        assert any(entry.actor == "system" and entry.decision == "apply" for entry in run.decision_history)

    asyncio.run(scenario())


def test_continuous_run_can_stop_after_current_task(tmp_path: Path) -> None:
    async def scenario() -> None:
        gate = threading.Event()
        tasks = [
            _task("TASK-1", runner="gemini-cli"),
            _task("TASK-2", runner="gemini-cli", depends_on=["TASK-1"]),
        ]
        roadmap_dir, roadmap = _seed_runtime_dir(tmp_path, tasks)
        engine = RunEngine("project-graceful-stop")
        engine.agent_router = _Router({"gemini-cli": _Adapter("gemini-cli", gate=gate)})

        run = await engine.start_run(
            "TASK-1",
            "gemini-cli",
            execution_mode=RunExecutionMode.CONTINUOUS,
            roadmap_dir=roadmap_dir,
            roadmap=roadmap,
        )

        for _ in range(40):
            if run.status == RunStatus.RUNNING:
                break
            await asyncio.sleep(0.05)

        updated = RunEngine.request_stop_after_current(run.run_id)
        assert updated is not None
        assert updated.stop_after_current is True

        gate.set()

        for _ in range(80):
            if run.status in (RunStatus.DONE, RunStatus.ERROR, RunStatus.CANCELLED):
                break
            await asyncio.sleep(0.05)

        assert run.status == RunStatus.DONE
        assert run.completed_task_ids == ["TASK-1"]

    asyncio.run(scenario())


def test_parallel_runs_allow_three_and_reject_fourth_with_monotonic_events(tmp_path: Path) -> None:
    async def scenario() -> None:
        gates = {
            "codex": threading.Event(),
            "claude-code": threading.Event(),
            "gemini-cli": threading.Event(),
        }
        tasks = [
            _task("TASK-1", runner="codex"),
            _task("TASK-2", runner="claude-code"),
            _task("TASK-3", runner="gemini-cli"),
            _task("TASK-4", runner="codex"),
        ]
        roadmap_dir, roadmap = _seed_runtime_dir(tmp_path, tasks)
        engine = RunEngine("project-parallel")
        engine.agent_router = _Router({
            "codex": _Adapter("codex", gate=gates["codex"]),
            "claude-code": _Adapter("claude-code", gate=gates["claude-code"]),
            "gemini-cli": _Adapter("gemini-cli", gate=gates["gemini-cli"]),
        })

        run_one = await engine.start_run("TASK-1", None, execution_mode=RunExecutionMode.CONTINUOUS, roadmap_dir=roadmap_dir, roadmap=roadmap)
        run_two = await engine.start_run("TASK-2", None, execution_mode=RunExecutionMode.CONTINUOUS, roadmap_dir=roadmap_dir, roadmap=roadmap)
        run_three = await engine.start_run("TASK-3", None, execution_mode=RunExecutionMode.CONTINUOUS, roadmap_dir=roadmap_dir, roadmap=roadmap)

        assert RunCoordinator.active_run_count("project-parallel") == 3

        with pytest.raises(RuntimeError, match="already has 3 active runs"):
            await engine.start_run("TASK-4", None, roadmap_dir=roadmap_dir, roadmap=roadmap)

        for gate in gates.values():
            gate.set()

        for run in (run_one, run_two, run_three):
            for _ in range(80):
                if run.status in (RunStatus.DONE, RunStatus.ERROR, RunStatus.CANCELLED):
                    break
                await asyncio.sleep(0.05)
            assert run.status == RunStatus.DONE

        events = [
            json.loads(line)
            for line in (tmp_path / "activity.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert [event["event_seq"] for event in events] == list(range(1, len(events) + 1))

    asyncio.run(scenario())


def test_parallel_runs_reject_same_agent_and_same_task(tmp_path: Path) -> None:
    async def scenario() -> None:
        gate = threading.Event()
        roadmap_dir, roadmap = _seed_runtime_dir(tmp_path, [
            _task("TASK-1", runner="codex"),
            _task("TASK-2", runner="codex"),
        ])
        engine = RunEngine("project-conflicts")
        engine.agent_router = _Router({
            "codex": _Adapter("codex", gate=gate),
            "claude-code": _Adapter("claude-code"),
        })

        run = await engine.start_run(
            "TASK-1",
            "codex",
            execution_mode=RunExecutionMode.CONTINUOUS,
            roadmap_dir=roadmap_dir,
            roadmap=roadmap,
        )

        with pytest.raises(RuntimeError, match="Agent codex is already executing another run"):
            await engine.start_run("TASK-2", "codex", roadmap_dir=roadmap_dir, roadmap=roadmap)

        with pytest.raises(RuntimeError, match="assigned to codex"):
            await engine.start_run("TASK-1", "claude-code", roadmap_dir=roadmap_dir, roadmap=roadmap, allow_in_progress=True)

        gate.set()
        for _ in range(80):
            if run.status in (RunStatus.DONE, RunStatus.ERROR, RunStatus.CANCELLED):
                break
            await asyncio.sleep(0.05)
        assert run.status == RunStatus.DONE

    asyncio.run(scenario())


def test_dependencies_block_task_execution(tmp_path: Path) -> None:
    async def scenario() -> None:
        roadmap_dir, roadmap = _seed_runtime_dir(tmp_path, [
            _task("TASK-1", runner="codex", status="todo"),
            _task("TASK-2", runner="gemini-cli", depends_on=["TASK-1"]),
        ])
        engine = RunEngine("project-deps")
        engine.agent_router = _Router({"gemini-cli": _Adapter("gemini-cli")})

        with pytest.raises(ValueError, match="Dependency TASK-1 is todo"):
            await engine.start_run("TASK-2", "gemini-cli", roadmap_dir=roadmap_dir, roadmap=roadmap)

    asyncio.run(scenario())


def test_codex_session_id_is_reused_across_context_builds() -> None:
    engine = RunEngine("project-codex-session")
    run_state = RunState(
        run_id="RUN-1",
        task_id="TASK-1",
        agent_id="codex",
    )

    engine._remember_agent_session_id(
        run_state=run_state,
        result={
            "metadata": {
                "codex_session_id": "0b6fd2c5-4e57-45c9-aa17-1cf32c6fbb2c",
            }
        },
    )

    context = engine._build_context(
        task=_task("TASK-2", runner="codex"),
        agent_id="codex",
        roadmap_id="roadmap.json",
        lessons=[],
        roadmap_dir=None,
    )

    assert context.metadata.get("codex_session_id") == "0b6fd2c5-4e57-45c9-aa17-1cf32c6fbb2c"


def test_start_run_allows_independent_task_when_projection_is_behind_activity(tmp_path: Path) -> None:
    async def scenario() -> None:
        roadmap_dir, roadmap = _seed_runtime_dir(tmp_path, [
            _task("TASK-1", runner="claude-code"),
            _task("TASK-2", runner="codex"),
        ])
        roadmap["meta"]["run"]["last_event_seq"] = 1
        roadmap["meta"]["run"]["projection_hash_sha256"] = Projector.compute_projection_hash(roadmap)
        _write_json(tmp_path / "roadmap.json", roadmap)
        (tmp_path / "activity.jsonl").write_text(
            json.dumps({
                "schema_version": "0.4.1",
                "event_id": "EV-00000002",
                "event_seq": 2,
                "ts": "2026-03-07T15:00:00Z",
                "actor": "claude-code",
                "action": "claim",
                "payload": {"task_id": "TASK-1", "prior_status": "todo"},
            }) + "\n" + json.dumps({
                "schema_version": "0.4.1",
                "event_id": "EV-00000003",
                "event_seq": 3,
                "ts": "2026-03-07T15:00:10Z",
                "actor": "claude-code",
                "action": "complete",
                "payload": {"task_id": "TASK-1", "prior_status": "in_progress"},
            }) + "\n",
            encoding="utf-8",
        )
        engine = RunEngine("project-stale")
        engine.agent_router = _Router({"codex": _Adapter("codex")})

        run = await engine.start_run(
            "TASK-2",
            "codex",
            execution_mode=RunExecutionMode.CONTINUOUS,
            roadmap_dir=roadmap_dir,
            roadmap=roadmap,
        )
        for _ in range(80):
            if run.status in (RunStatus.DONE, RunStatus.ERROR, RunStatus.CANCELLED):
                break
            await asyncio.sleep(0.05)
        assert run.status == RunStatus.DONE

    asyncio.run(scenario())


def test_start_run_rejects_in_progress_task_owned_by_other_agent(tmp_path: Path) -> None:
    async def scenario() -> None:
        roadmap_dir, roadmap = _seed_runtime_dir(tmp_path, [
            _task("TASK-1", runner="codex", status="in_progress"),
        ])
        roadmap["tasks"][0]["assigned_to"] = "codex"
        roadmap["tasks"][0]["started_at"] = "2026-03-07T15:00:00Z"
        roadmap["indexes"]["by_status"] = {"todo": 0, "in_progress": 1, "review": 0, "done": 0}
        roadmap["meta"]["run"]["projection_hash_sha256"] = Projector.compute_projection_hash(roadmap)
        _write_json(tmp_path / "roadmap.json", roadmap)
        engine = RunEngine("project-owner")
        engine.agent_router = _Router({"claude-code": _Adapter("claude-code")})

        with pytest.raises(RuntimeError, match="assigned to codex"):
            await engine.start_run("TASK-1", "claude-code", roadmap_dir=roadmap_dir, roadmap=roadmap, allow_in_progress=True)

    asyncio.run(scenario())
