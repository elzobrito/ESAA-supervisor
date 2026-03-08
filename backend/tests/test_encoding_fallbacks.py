import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.api.routes_projects import store
from app.core.canonical_store import CanonicalStore
from app.core.projector import Projector
from app.main import app


client = TestClient(app)


def _write_utf8_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_canonical_store_loads_cp1252_roadmap() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        roadmap_dir = Path(tmp_dir) / ".roadmap"
        roadmap_dir.mkdir()
        roadmap = {
            "meta": {
                "schema_version": "0.4.0",
                "run": {
                    "last_event_seq": 0,
                    "verify_status": "ok",
                    "projection_hash_sha256": "placeholder",
                },
            },
            "project": {"name": "Sessão"},
            "tasks": [],
            "indexes": {"by_status": {"todo": 0, "in_progress": 0, "review": 0, "done": 0}, "by_kind": {"spec": 0, "impl": 0, "qa": 0}, "by_preferred_runner": {}},
        }
        roadmap["meta"]["run"]["projection_hash_sha256"] = Projector.compute_projection_hash(roadmap)
        (roadmap_dir / "roadmap.json").write_bytes(json.dumps(roadmap, ensure_ascii=False, indent=2).encode("cp1252"))
        _write_utf8_json(roadmap_dir / "issues.json", {"issues": []})
        _write_utf8_json(roadmap_dir / "lessons.json", {"lessons": []})
        (roadmap_dir / "activity.jsonl").write_text("", encoding="utf-8")

        state = CanonicalStore(tmp_dir)
        state.load_project("demo", str(roadmap_dir))
        data = state.get_state()

    assert data.roadmap["project"]["name"] == "Sessão"


def test_projector_load_projection_reads_cp1252_files() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        roadmap_dir = Path(tmp_dir)
        roadmap = {
            "meta": {
                "schema_version": "0.4.0",
                "run": {
                    "last_event_seq": 0,
                    "verify_status": "ok",
                    "projection_hash_sha256": "placeholder",
                },
            },
            "project": {"name": "Criptografia"},
            "tasks": [],
            "indexes": {"by_status": {"todo": 0, "in_progress": 0, "review": 0, "done": 0}, "by_kind": {"spec": 0, "impl": 0, "qa": 0}, "by_preferred_runner": {}},
        }
        roadmap["meta"]["run"]["projection_hash_sha256"] = Projector.compute_projection_hash(roadmap)
        (roadmap_dir / "roadmap.json").write_bytes(json.dumps(roadmap, ensure_ascii=False, indent=2).encode("cp1252"))
        _write_utf8_json(roadmap_dir / "issues.json", {"issues": []})
        _write_utf8_json(roadmap_dir / "lessons.json", {"lessons": []})
        (roadmap_dir / "activity.jsonl").write_text("", encoding="utf-8")

        loaded_roadmap, _, _ = Projector(tmp_dir).load_projection()

    assert loaded_roadmap["project"]["name"] == "Criptografia"


def test_issue_resolve_accepts_cp1252_issues_projection() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        roadmap_dir = Path(tmp_dir)
        roadmap = {
            "meta": {
                "schema_version": "0.4.0",
                "run": {
                    "last_event_seq": 0,
                    "verify_status": "ok",
                    "projection_hash_sha256": "placeholder",
                },
            },
            "project": {"name": "Issues"},
            "tasks": [],
            "indexes": {"by_status": {"todo": 0, "in_progress": 0, "review": 0, "done": 0}, "by_kind": {"spec": 0, "impl": 0, "qa": 0}, "by_preferred_runner": {}},
        }
        roadmap["meta"]["run"]["projection_hash_sha256"] = Projector.compute_projection_hash(roadmap)
        _write_utf8_json(roadmap_dir / "roadmap.json", roadmap)
        issues = {
            "meta": {"schema_version": "0.4.0", "last_event_seq": 0, "updated_at": "2026-03-07T00:00:00Z"},
            "issues": [
                {
                    "issue_id": "ISS-1",
                    "status": "open",
                    "severity": "medium",
                    "title": "Correção manual",
                    "resolution": None,
                    "links": {"reported_by_task_id": "SEC-001", "fixes_task_id": None},
                    "timeline": {"created_event_seq": 0, "resolved_event_seq": None},
                }
            ],
            "indexes": {"open_by_baseline": {}},
        }
        (roadmap_dir / "issues.json").write_bytes(json.dumps(issues, ensure_ascii=False, indent=2).encode("cp1252"))
        _write_utf8_json(roadmap_dir / "lessons.json", {"lessons": []})
        (roadmap_dir / "activity.jsonl").write_text("", encoding="utf-8")

        store.load_project("test-project", tmp_dir)
        response = client.post("/api/v1/projects/test-project/issues/resolve", json={"issue_id": "ISS-1"})

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
