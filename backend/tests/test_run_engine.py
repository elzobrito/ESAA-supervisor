import asyncio

from app.core.run_engine import RunEngine
from app.models.agent_result import AgentMetadata, AgentPayload, AgentResult
from app.models.run_state import RunExecutionMode, RunStatus


class _FakeAdapter:
    actor = "gemini-cli"

    def run(self, context, prompt, log_callback=None):
        if log_callback is not None:
            log_callback("stdout", "fake adapter executed")
        return AgentResult(
            action="issue.report",
            actor=self.actor,
            payload=AgentPayload(task_id=context.task_id, error="simulated issue"),
            metadata=AgentMetadata(
                exit_code=0,
                duration_ms=1,
                raw_output='{"action":"issue.report"}',
                stdout="",
                stderr="",
                command=["fake-agent"],
            ),
        )


class _FakeRouter:
    def get_adapter(self, agent_id: str):
        return _FakeAdapter()


class _CompleteAdapter:
    actor = "gemini-cli"

    def __init__(self, release_event: asyncio.Event | None = None):
        self.release_event = release_event

    def run(self, context, prompt, log_callback=None):
        if self.release_event is not None:
            asyncio.run(self.release_event.wait())
        if log_callback is not None:
            log_callback("stdout", f"completed {context.task_id}")
        return AgentResult(
            action="complete",
            actor=self.actor,
            payload=AgentPayload(task_id=context.task_id),
            metadata=AgentMetadata(
                exit_code=0,
                duration_ms=1,
                raw_output='{"action":"complete"}',
                stdout="",
                stderr="",
                command=["fake-agent"],
            ),
        )


class _CompleteRouter:
    def __init__(self, release_event: asyncio.Event | None = None):
        self.adapter = _CompleteAdapter(release_event=release_event)

    def get_adapter(self, agent_id: str):
        return self.adapter


def test_cancelled_run_does_not_finish_as_done() -> None:
    async def scenario() -> None:
        engine = RunEngine("project-cancel")
        engine.agent_router = _FakeRouter()
        run = await engine.start_run("TASK-1", "gemini-cli")

        await asyncio.sleep(0.05)
        cancelled = RunEngine.cancel_run("project-cancel", run.run_id)
        await asyncio.sleep(0.1)

        assert cancelled is True
        assert run.status == RunStatus.CANCELLED
        assert run.ended_at is not None
        assert any("cancelled" in entry.content.lower() for entry in run.logs)

    asyncio.run(scenario())


def test_run_waits_for_manual_decision_before_finishing() -> None:
    async def scenario() -> None:
        engine = RunEngine("project-manual")
        engine.agent_router = _FakeRouter()
        run = await engine.start_run("TASK-2", "gemini-cli")

        for _ in range(40):
            if run.status == RunStatus.WAITING_INPUT:
                break
            await asyncio.sleep(0.05)

        assert run.status == RunStatus.WAITING_INPUT
        assert run.awaiting_decision is True
        assert run.proposed_action is not None
        assert len(run.decision_history) == 1
        assert run.decision_history[0].stage == "proposal"

        RunEngine.submit_decision(run.run_id, "reject")

        for _ in range(40):
            if run.status in (RunStatus.CANCELLED, RunStatus.DONE, RunStatus.ERROR):
                break
            await asyncio.sleep(0.05)

        assert run.status == RunStatus.CANCELLED
        assert run.ended_at is not None
        assert len(run.decision_history) == 2
        assert run.decision_history[-1].decision == "reject"

    asyncio.run(scenario())


def test_continuous_run_auto_applies_and_moves_to_next_task() -> None:
    async def scenario() -> None:
        engine = RunEngine("project-continuous")
        engine.agent_router = _CompleteRouter()
        selected_tasks = iter([
            {"task_id": "TASK-2", "task_kind": "impl", "title": "Task 2", "description": "desc", "status": "todo"},
            None,
        ])
        engine._select_next_task = lambda **kwargs: next(selected_tasks)
        engine._claim_task = lambda *args, **kwargs: None
        applied_actions: list[tuple[str, str]] = []
        engine._apply_selected_action = lambda **kwargs: applied_actions.append((kwargs["run_state"].task_id, kwargs["selected_action"]))

        run = await engine.start_run(
            "TASK-1",
            "gemini-cli",
            execution_mode=RunExecutionMode.CONTINUOUS,
            roadmap_dir="C:/tmp/nonexistent-roadmap-dir",
            roadmap={"tasks": [
                {"task_id": "TASK-1", "task_kind": "impl", "title": "Task 1", "description": "desc", "status": "todo"},
                {"task_id": "TASK-2", "task_kind": "impl", "title": "Task 2", "description": "desc", "status": "todo"},
            ]},
        )

        for _ in range(60):
            if run.status in (RunStatus.DONE, RunStatus.ERROR, RunStatus.CANCELLED):
                break
            await asyncio.sleep(0.05)

        assert run.status == RunStatus.DONE
        assert run.awaiting_decision is False
        assert run.completed_task_ids == ["TASK-1", "TASK-2"]
        assert applied_actions == [("TASK-1", "complete"), ("TASK-2", "complete")]
        assert any(entry.actor == "system" and entry.decision == "apply" for entry in run.decision_history)

    asyncio.run(scenario())


def test_continuous_run_can_stop_after_current_task() -> None:
    async def scenario() -> None:
        release_event = asyncio.Event()
        engine = RunEngine("project-graceful-stop")
        engine.agent_router = _CompleteRouter(release_event=release_event)
        engine._claim_task = lambda *args, **kwargs: None
        next_task_called = False

        def _unexpected_next_task(**kwargs):
            nonlocal next_task_called
            next_task_called = True
            return {"task_id": "TASK-2"}

        engine._select_next_task = _unexpected_next_task
        engine._apply_selected_action = lambda **kwargs: None

        run = await engine.start_run(
            "TASK-1",
            "gemini-cli",
            execution_mode=RunExecutionMode.CONTINUOUS,
            roadmap_dir="C:/tmp/nonexistent-roadmap-dir",
            roadmap={"tasks": [
                {"task_id": "TASK-1", "task_kind": "impl", "title": "Task 1", "description": "desc", "status": "todo"},
            ]},
        )

        for _ in range(40):
            if run.status == RunStatus.RUNNING:
                break
            await asyncio.sleep(0.05)

        updated = RunEngine.request_stop_after_current(run.run_id)
        assert updated is not None
        assert updated.stop_after_current is True

        release_event.set()

        for _ in range(60):
            if run.status in (RunStatus.DONE, RunStatus.ERROR, RunStatus.CANCELLED):
                break
            await asyncio.sleep(0.05)

        assert run.status == RunStatus.DONE
        assert run.completed_task_ids == ["TASK-1"]
        assert next_task_called is False

    asyncio.run(scenario())
