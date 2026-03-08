import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes_projects import store
from app.main import app


client = TestClient(app)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _seed_project(tmp_dir: str) -> None:
    roadmap_dir = Path(tmp_dir)
    _write_json(
        roadmap_dir / "roadmap.json",
        {
            "meta": {
                "schema_version": "0.4.0",
                "run": {
                    "last_event_seq": 0,
                    "verify_status": "ok",
                    "projection_hash_sha256": "placeholder",
                },
            },
            "project": {"name": "Test"},
            "tasks": [],
            "indexes": {"by_status": {"todo": 0, "in_progress": 0, "review": 0, "done": 0}, "by_kind": {"spec": 0, "impl": 0, "qa": 0}, "by_preferred_runner": {}},
        },
    )
    _write_json(
        roadmap_dir / "issues.json",
        {
            "meta": {"schema_version": "0.4.0", "last_event_seq": 0, "updated_at": "2026-03-07T00:00:00Z"},
            "issues": [],
            "indexes": {"open_by_baseline": {}},
        },
    )
    _write_json(
        roadmap_dir / "lessons.json",
        {
            "meta": {"schema_version": "0.4.0", "updated_at": "2026-03-07T00:00:00Z"},
            "lessons": [],
            "indexes": {"by_task_kind": {}, "by_enforcement_applies_to": {}},
        },
    )
    (roadmap_dir / "activity.jsonl").write_text("", encoding="utf-8")


def test_state_returns_200_for_cp1252_roadmap_variant() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        _seed_project(tmp_dir)
        roadmap_security = {
            "meta": {
                "schema_version": "0.4.0",
                "run": {
                    "last_event_seq": 0,
                    "verify_status": "ok",
                    "projection_hash_sha256": "placeholder",
                },
            },
            "project": {"name": "Segurança"},
            "tasks": [
                {
                    "task_id": "SEC-001",
                    "task_kind": "impl",
                    "title": "Auditar sessão",
                    "description": "Revisar proteção de sessão com ação corretiva.",
                    "status": "todo",
                    "depends_on": [],
                    "targets": [],
                    "outputs": {"files": []},
                }
            ],
            "indexes": {"by_status": {"todo": 1, "in_progress": 0, "review": 0, "done": 0}, "by_kind": {"spec": 0, "impl": 1, "qa": 0}, "by_preferred_runner": {}},
        }
        from app.core.projector import Projector
        roadmap_security["meta"]["run"]["projection_hash_sha256"] = Projector.compute_projection_hash(roadmap_security)
        (Path(tmp_dir) / "roadmap.security.json").write_bytes(
            json.dumps(roadmap_security, ensure_ascii=False, indent=2).encode("cp1252")
        )

        store.load_project("test-project", tmp_dir)
        response = client.get("/api/v1/projects/test-project/state", params={"roadmap": "roadmap.security.json"})

    assert response.status_code == 200
    data = response.json()
    assert data["selected_roadmap_load_status"] == "warning"
    assert "fallback encoding cp1252" in data["selected_roadmap_warning"]


def test_state_returns_409_for_unrecoverable_selected_roadmap() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        _seed_project(tmp_dir)
        (Path(tmp_dir) / "roadmap.security.json").write_bytes(b'{"tasks": [}\xe7')

        store.load_project("test-project", tmp_dir)
        response = client.get("/api/v1/projects/test-project/state", params={"roadmap": "roadmap.security.json"})

    assert response.status_code == 409
    assert "could not be decoded" in response.json()["detail"] or "Invalid JSON" in response.json()["detail"]


def test_repair_integrity_normalizes_cp1252_files() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        _seed_project(tmp_dir)
        roadmap_security = {
            "meta": {
                "schema_version": "0.4.0",
                "run": {
                    "last_event_seq": 0,
                    "verify_status": "ok",
                    "projection_hash_sha256": "placeholder",
                },
            },
            "project": {"name": "Segurança"},
            "tasks": [],
            "indexes": {"by_status": {"todo": 0, "in_progress": 0, "review": 0, "done": 0}, "by_kind": {"spec": 0, "impl": 0, "qa": 0}, "by_preferred_runner": {}},
        }
        from app.core.projector import Projector
        roadmap_security["meta"]["run"]["projection_hash_sha256"] = Projector.compute_projection_hash(roadmap_security)
        roadmap_path = Path(tmp_dir) / "roadmap.security.json"
        roadmap_path.write_bytes(json.dumps(roadmap_security, ensure_ascii=False, indent=2).encode("cp1252"))

        store.load_project("test-project", tmp_dir)
        response = client.post("/api/v1/projects/test-project/integrity/repair", json={"roadmap_id": "roadmap.security.json"})

        normalized_bytes = roadmap_path.read_bytes()

    assert response.status_code == 200
    assert "roadmap.security.json" in response.json()["normalized_files"]
    normalized_bytes.decode("utf-8")
