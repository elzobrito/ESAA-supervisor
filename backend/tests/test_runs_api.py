from datetime import datetime
from unittest.mock import MagicMock, patch
import tempfile
import json

from fastapi.testclient import TestClient

from app.main import app
from app.models.run_state import RunExecutionMode, RunState, RunStatus

client = TestClient(app)

MOCK_PROJECT_ID = "test-project"

MOCK_ROADMAP = {
    "tasks": [
        {
            "task_id": "T-001",
            "task_kind": "impl",
            "title": "Test task",
            "description": "desc",
            "status": "todo",
            "depends_on": [],
            "targets": [],
            "outputs": {"files": []},
            "immutability": {"done_is_immutable": True},
            "required_verification": [],
        }
    ],
    "indexes": {"by_status": {"todo": 1, "in_progress": 0, "review": 0, "done": 0}},
}

MOCK_STATE = MagicMock()
MOCK_STATE.roadmap = MOCK_ROADMAP
MOCK_STATE.issues = {"issues": []}
MOCK_STATE.lessons = {"lessons": []}
MOCK_STATE.artifacts = []
MOCK_STATE.last_event_seq = 10
MOCK_STATE.is_consistent = True
MOCK_STATE.project.id = MOCK_PROJECT_ID
MOCK_STATE.project.name = "Test"
MOCK_STATE.project.base_path = "/tmp"
MOCK_STATE.project.is_active = True

MOCK_PROJECT = MagicMock()
MOCK_PROJECT.id = MOCK_PROJECT_ID
MOCK_PROJECT.base_path = "/tmp"


def _mock_store(store):
    store.active_project = MOCK_PROJECT
    store.get_state.return_value = MOCK_STATE
    store.load_project.return_value = None


def test_root_returns_running() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_eligibility_report_returns_eligible_task() -> None:
    with patch("app.api.routes_runs.store") as mock_store:
        _mock_store(mock_store)
        response = client.get(f"/api/v1/projects/{MOCK_PROJECT_ID}/runs/eligibility")

    assert response.status_code == 200
    data = response.json()
    assert data["eligible_count"] == 1
    assert data["tasks"][0]["task_id"] == "T-001"
    assert data["tasks"][0]["is_eligible"] is True


def test_start_next_run_returns_run_response() -> None:
    mock_run = RunState(
        run_id="run-abc",
        task_id="T-001",
        agent_id="gemini-cli",
        status=RunStatus.PREFLIGHT,
        started_at=datetime(2026, 3, 7, 4, 0, 0),
    )
    with patch("app.api.routes_runs.store") as mock_store, \
         patch("app.api.routes_runs.RunEngine") as MockEngine, \
         patch("app.api.routes_runs._discover_roadmap_variants", return_value={"roadmap.json": {"payload": MOCK_ROADMAP}}):
        _mock_store(mock_store)
        instance = MockEngine.return_value
        import asyncio
        async def fake_start(*args, **kwargs):
            return mock_run
        instance.start_run.side_effect = fake_start

        response = client.post(
            f"/api/v1/projects/{MOCK_PROJECT_ID}/runs/next",
            json={"agent_id": "gemini-cli"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "run-abc"
    assert data["task_id"] == "T-001"
    assert data["status"] == "preflight"


def test_start_next_run_passes_execution_mode() -> None:
    mock_run = RunState(
        run_id="run-cont",
        task_id="T-001",
        agent_id="gemini-cli",
        status=RunStatus.PREFLIGHT,
        started_at=datetime(2026, 3, 7, 4, 0, 0),
    )
    with patch("app.api.routes_runs.store") as mock_store, \
         patch("app.api.routes_runs.RunEngine") as MockEngine, \
         patch("app.api.routes_runs._discover_roadmap_variants", return_value={"roadmap.json": {"payload": MOCK_ROADMAP}}):
        _mock_store(mock_store)
        instance = MockEngine.return_value

        async def fake_start(*args, **kwargs):
            return mock_run

        instance.start_run.side_effect = fake_start

        response = client.post(
            f"/api/v1/projects/{MOCK_PROJECT_ID}/runs/next",
            json={"agent_id": "gemini-cli", "execution_mode": "continuous"},
        )

    assert response.status_code == 200
    assert MockEngine.return_value.start_run.call_args.args[3] == RunExecutionMode.CONTINUOUS


def test_start_next_run_422_when_no_eligible_task() -> None:
    no_task_state = MagicMock()
    no_task_state.roadmap = {"tasks": [], "indexes": {}}
    no_task_state.issues = {"issues": []}

    with patch("app.api.routes_runs.store") as mock_store, \
         patch("app.api.routes_runs._discover_roadmap_variants", return_value={"roadmap.json": {"payload": {"tasks": []}}}):
        mock_store.active_project = MOCK_PROJECT
        mock_store.get_state.return_value = no_task_state

        response = client.post(
            f"/api/v1/projects/{MOCK_PROJECT_ID}/runs/next",
            json={"agent_id": "gemini-cli"},
        )

    assert response.status_code == 422


def test_cancel_run_404_when_not_found() -> None:
    with patch("app.api.routes_runs.store") as mock_store:
        _mock_store(mock_store)
        with patch("app.api.routes_runs.RunEngine.get_run_state", return_value=None):
            response = client.delete(
                f"/api/v1/projects/{MOCK_PROJECT_ID}/runs/nonexistent-run-id"
            )

    assert response.status_code == 404


def test_get_run_status_404_when_not_found() -> None:
    with patch("app.api.routes_runs.store") as mock_store:
        _mock_store(mock_store)
        with patch("app.api.routes_runs.RunEngine.get_run_state", return_value=None):
            response = client.get(
                f"/api/v1/projects/{MOCK_PROJECT_ID}/runs/nonexistent-run-id"
            )

    assert response.status_code == 404


def test_list_runs_returns_active_runs() -> None:
    mock_run = RunState(
        run_id="run-list",
        task_id="T-001",
        agent_id="gemini-cli",
        model_id="gemini-2.5-pro",
        status=RunStatus.RUNNING,
        started_at=datetime(2026, 3, 7, 4, 0, 0),
    )
    with patch("app.api.routes_runs.store") as mock_store, \
         patch("app.api.routes_runs.RunEngine.list_runs", return_value=[mock_run]):
        _mock_store(mock_store)
        response = client.get(f"/api/v1/projects/{MOCK_PROJECT_ID}/runs")

    assert response.status_code == 200
    assert response.json()[0]["run_id"] == "run-list"
    assert response.json()[0]["model_id"] == "gemini-2.5-pro"


def test_stop_after_current_activates_graceful_stop() -> None:
    mock_run = RunState(
        run_id="run-stop",
        task_id="T-001",
        agent_id="gemini-cli",
        execution_mode=RunExecutionMode.CONTINUOUS,
        status=RunStatus.RUNNING,
        started_at=datetime(2026, 3, 7, 4, 0, 0),
        stop_after_current=True,
    )
    with patch("app.api.routes_runs.store") as mock_store:
        _mock_store(mock_store)
        with patch("app.api.routes_runs.RunEngine.get_run_state", return_value=mock_run), \
             patch("app.api.routes_runs.RunEngine.request_stop_after_current", return_value=mock_run):
            response = client.post(
                f"/api/v1/projects/{MOCK_PROJECT_ID}/runs/{mock_run.run_id}/stop-after-current"
            )

    assert response.status_code == 200
    assert response.json()["stop_after_current"] is True


def test_start_task_run_blocks_when_dependency_is_pending() -> None:
    blocked_roadmap = {
        "tasks": [
            {
                "task_id": "T-001",
                "task_kind": "impl",
                "title": "Parent",
                "description": "desc",
                "status": "todo",
                "depends_on": [],
                "targets": [],
                "outputs": {"files": []},
                "immutability": {"done_is_immutable": True},
                "required_verification": [],
            },
            {
                "task_id": "T-002",
                "task_kind": "impl",
                "title": "Child",
                "description": "desc",
                "status": "todo",
                "depends_on": ["T-001"],
                "targets": [],
                "outputs": {"files": []},
                "immutability": {"done_is_immutable": True},
                "required_verification": [],
            },
        ],
        "indexes": {"by_status": {"todo": 2, "in_progress": 0, "review": 0, "done": 0}},
    }
    with patch("app.api.routes_runs.store") as mock_store, \
         patch("app.api.routes_runs._discover_roadmap_variants", return_value={"roadmap.json": {"payload": blocked_roadmap}}):
        _mock_store(mock_store)
        response = client.post(
            f"/api/v1/projects/{MOCK_PROJECT_ID}/runs/task",
            json={"task_id": "T-002", "agent_id": "gemini-cli"},
        )

    assert response.status_code == 422
    assert "Dependency T-001 is todo" in str(response.json()["detail"])


def test_start_task_run_allows_projection_lag_for_independent_task() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        roadmap = {
            "meta": {
                "schema_version": "0.4.0",
                "run": {
                    "last_event_seq": 1,
                    "verify_status": "ok",
                    "projection_hash_sha256": "placeholder",
                }
            },
            "project": {"name": "Test"},
            "tasks": [
                {
                    "task_id": "T-001",
                    "task_kind": "impl",
                    "title": "Task 1",
                    "description": "desc",
                    "status": "todo",
                    "depends_on": [],
                    "targets": [],
                    "outputs": {"files": []},
                    "immutability": {"done_is_immutable": True},
                    "required_verification": [],
                },
                {
                    "task_id": "T-002",
                    "task_kind": "impl",
                    "title": "Task",
                    "description": "desc",
                    "status": "todo",
                    "depends_on": [],
                    "targets": [],
                    "outputs": {"files": []},
                    "immutability": {"done_is_immutable": True},
                    "required_verification": [],
                }
            ],
            "indexes": {"by_status": {"todo": 2, "in_progress": 0, "review": 0, "done": 0}, "by_kind": {"spec": 0, "impl": 2, "qa": 0}, "by_preferred_runner": {}},
        }
        from app.core.projector import Projector
        roadmap["meta"]["run"]["projection_hash_sha256"] = Projector.compute_projection_hash(roadmap)
        with open(f"{tmp_dir}\\roadmap.json", "w", encoding="utf-8") as handle:
            json.dump(roadmap, handle)
        with open(f"{tmp_dir}\\issues.json", "w", encoding="utf-8") as handle:
            json.dump({"issues": []}, handle)
        with open(f"{tmp_dir}\\lessons.json", "w", encoding="utf-8") as handle:
            json.dump({"lessons": []}, handle)
        with open(f"{tmp_dir}\\activity.jsonl", "w", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "schema_version": "0.4.1",
                "event_id": "EV-00000002",
                "event_seq": 2,
                "ts": "2026-03-07T15:00:00Z",
                "actor": "claude-code",
                "action": "claim",
                "payload": {"task_id": "T-001", "prior_status": "todo"},
            }) + "\n")

        stale_project = MagicMock()
        stale_project.id = MOCK_PROJECT_ID
        stale_project.base_path = tmp_dir

        with patch("app.api.routes_runs.store") as mock_store:
            mock_store.active_project = stale_project
            mock_store.get_state.return_value = MOCK_STATE
            with patch("app.api.routes_runs.RunEngine") as MockEngine:
                async def fake_start(*args, **kwargs):
                    return RunState(
                        run_id="run-lag",
                        task_id="T-002",
                        agent_id="gemini-cli",
                        status=RunStatus.PREFLIGHT,
                        started_at=datetime(2026, 3, 7, 4, 0, 0),
                    )
                MockEngine.return_value.start_run.side_effect = fake_start
                response = client.post(
                    f"/api/v1/projects/{MOCK_PROJECT_ID}/runs/task",
                    json={"task_id": "T-002", "agent_id": "gemini-cli"},
                )

    assert response.status_code == 200


def test_start_task_run_returns_409_for_in_progress_task_of_other_agent() -> None:
    owned_roadmap = {
        "tasks": [
            {
                "task_id": "T-001",
                "task_kind": "impl",
                "title": "Task",
                "description": "desc",
                "status": "in_progress",
                "assigned_to": "codex",
                "started_at": "2026-03-07T15:00:00Z",
                "depends_on": [],
                "targets": [],
                "outputs": {"files": []},
                "immutability": {"done_is_immutable": True},
                "required_verification": [],
                "planning": {"preferred_runner": "claude-code"},
            }
        ],
        "indexes": {"by_status": {"todo": 0, "in_progress": 1, "review": 0, "done": 0}},
    }
    with patch("app.api.routes_runs.store") as mock_store, \
         patch("app.api.routes_runs._discover_roadmap_variants", return_value={"roadmap.json": {"payload": owned_roadmap}}), \
         patch("app.api.routes_runs.RunEngine") as MockEngine:
        _mock_store(mock_store)

        async def fake_start(*args, **kwargs):
            raise RuntimeError("Task T-001 is in_progress and assigned to codex. Regress it to todo before switching to claude-code.")

        MockEngine.return_value.start_run.side_effect = fake_start
        response = client.post(
            f"/api/v1/projects/{MOCK_PROJECT_ID}/runs/task",
            json={"task_id": "T-001", "agent_id": "claude-code"},
        )

    assert response.status_code == 409
    assert "assigned to codex" in response.json()["detail"]


def test_patch_task_planning_persists_only_preferred_runner() -> None:
    roadmap = {
        "tasks": [
            {
                "task_id": "T-001",
                "task_kind": "impl",
                "title": "Task",
                "description": "desc",
                "status": "todo",
                "depends_on": [],
                "targets": [],
                "outputs": {"files": []},
                "immutability": {"done_is_immutable": True},
                "required_verification": [],
                "planning": {"preferred_runner": "codex"},
            }
        ]
    }
    with patch("app.api.routes_tasks.store") as mock_store, \
         patch("app.api.routes_tasks._discover_roadmap_variants", return_value={"roadmap.json": {"payload": roadmap}}), \
         patch("app.api.routes_tasks.EventWriter") as MockWriter, \
         patch("app.api.routes_tasks.Projector"):
        _mock_store(mock_store)
        writer = MockWriter.return_value
        writer.append_event.return_value = {"event_seq": 1, "payload": {"planning": {"preferred_runner": "gemini-cli"}}}
        response = client.patch(
            f"/api/v1/projects/{MOCK_PROJECT_ID}/tasks/T-001/planning",
            json={"preferred_runner": "gemini-cli"},
        )

    assert response.status_code == 200
    assert response.json()["planning"] == {"preferred_runner": "gemini-cli"}
