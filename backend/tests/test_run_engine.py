import asyncio

from app.core.run_engine import RunEngine
from app.models.agent_result import AgentMetadata, AgentPayload, AgentResult
from app.models.run_state import RunStatus


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
