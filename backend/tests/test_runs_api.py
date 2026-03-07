import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.models.run_state import RunState, RunStatus
from datetime import datetime

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
         patch("app.api.routes_runs.RunEngine") as MockEngine:
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


def test_start_next_run_422_when_no_eligible_task() -> None:
    no_task_state = MagicMock()
    no_task_state.roadmap = {"tasks": [], "indexes": {}}
    no_task_state.issues = {"issues": []}

    with patch("app.api.routes_runs.store") as mock_store:
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
