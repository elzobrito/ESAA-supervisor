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


def test_repair_integrity_trusts_self_consistent_projection_with_stale_cursor() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        _seed_project(tmp_dir)
        roadmap_security = {
            "meta": {
                "schema_version": "0.4.0",
                "run": {
                    "last_event_seq": 0,
                    "verify_status": "error",
                    "projection_hash_sha256": "placeholder",
                    "integrity_error": {
                        "message": "Task SEC-001 expected status todo, got done",
                        "event_seq": 1,
                        "event_id": "EV-00000001",
                        "task_id": "SEC-001",
                        "actor": "claude-code",
                        "action": "claim",
                    },
                },
            },
            "project": {"name": "Segurança"},
            "tasks": [
                {
                    "task_id": "SEC-001",
                    "task_kind": "impl",
                    "title": "Auditar sessão",
                    "description": "Revisar proteção de sessão com ação corretiva.",
                    "status": "done",
                    "depends_on": [],
                    "targets": [],
                    "outputs": {"files": []},
                    "assigned_to": "claude-code",
                    "started_at": "2026-03-07T00:00:00Z",
                    "completed_at": "2026-03-07T00:02:00Z",
                    "verification": {"checks": ["ok"]},
                }
            ],
            "indexes": {"by_status": {"todo": 0, "in_progress": 0, "review": 0, "done": 1}, "by_kind": {"spec": 0, "impl": 1, "qa": 0}, "by_preferred_runner": {}},
        }
        from app.core.projector import Projector
        roadmap_security["meta"]["run"]["projection_hash_sha256"] = Projector.compute_projection_hash(roadmap_security)
        roadmap_path = Path(tmp_dir) / "roadmap.security.json"
        _write_json(roadmap_path, roadmap_security)
        (Path(tmp_dir) / "activity.jsonl").write_text(
            "\n".join(
                [
                    json.dumps({
                        "schema_version": "0.4.1",
                        "event_id": "EV-00000001",
                        "event_seq": 1,
                        "ts": "2026-03-07T00:00:00Z",
                        "actor": "claude-code",
                        "action": "claim",
                        "payload": {"task_id": "SEC-001", "prior_status": "todo"},
                    }),
                    json.dumps({
                        "schema_version": "0.4.1",
                        "event_id": "EV-00000002",
                        "event_seq": 2,
                        "ts": "2026-03-07T00:01:00Z",
                        "actor": "claude-code",
                        "action": "complete",
                        "payload": {"task_id": "SEC-001", "prior_status": "in_progress", "verification": {"checks": ["ok"]}},
                    }),
                    json.dumps({
                        "schema_version": "0.4.1",
                        "event_id": "EV-00000003",
                        "event_seq": 3,
                        "ts": "2026-03-07T00:02:00Z",
                        "actor": "orchestrator",
                        "action": "review",
                        "payload": {"task_id": "SEC-001", "prior_status": "review", "decision": "approve"},
                    }),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        store.load_project("test-project", tmp_dir)
        response = client.post("/api/v1/projects/test-project/integrity/repair", json={"roadmap_id": "roadmap.security.json"})
        repaired = json.loads(roadmap_path.read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert "roadmap.security.json" in response.json()["repaired_roadmaps"]
    assert repaired["meta"]["run"]["last_event_seq"] == 3
    assert repaired["meta"]["run"]["verify_status"] == "ok"
    assert "integrity_error" not in repaired["meta"]["run"]


def test_repair_integrity_normalizes_shared_issues_and_lessons_projections() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        _seed_project(tmp_dir)
        issues_payload = {
            "issues": [
                {
                    "issue_id": "ISS-LEGACY-1",
                    "status": "resolved",
                    "severity": "medium",
                    "title": "Projection drift",
                    "evidence": "Legacy issue evidence as plain text.",
                    "resolution": "Fixed manually.",
                    "task_id": "SEC-001",
                    "links": {"reported_by_task_id": "SEC-001", "fixes_task_id": "SEC-001", "hotfix_task_id": None},
                    "timeline": {"created_event_seq": None, "resolved_event_seq": None},
                }
            ],
            "meta": {
                "last_event_seq": 0,
                "updated_at": "2026-03-08T00:00:00Z",
            },
            "indexes": {"open_by_baseline": {}},
        }
        lessons_payload = {
            "lessons": [
                {
                    "lesson_id": "LES-0099",
                    "title": "Projection artifacts need canonical metadata",
                    "mistake": "Issues and lessons were rewritten without canonical meta fields.",
                    "rule": "Always rewrite shared projection artifacts through sync_projection before validating integrity.",
                    "scope": {"task_kinds": ["impl", "qa"]},
                    "enforcement": {"mode": "require_step", "applies_to": "workflow_gate"},
                }
            ],
            "meta": {
                "updated_at": "2026-03-08T00:00:00Z",
            },
            "indexes": {"by_task_kind": {}, "by_enforcement_applies_to": {}},
        }
        _write_json(Path(tmp_dir) / "issues.json", issues_payload)
        _write_json(Path(tmp_dir) / "lessons.json", lessons_payload)

        store.load_project("test-project", tmp_dir)
        response = client.post("/api/v1/projects/test-project/integrity/repair", json={"roadmap_id": "roadmap.json"})
        repaired_issues = json.loads((Path(tmp_dir) / "issues.json").read_text(encoding="utf-8"))
        repaired_lessons = json.loads((Path(tmp_dir) / "lessons.json").read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert repaired_issues["meta"]["generated_by"] == "esaa.project"
    assert repaired_issues["meta"]["source_event_store"] == ".roadmap/activity.jsonl"
    assert repaired_issues["issues"][0]["evidence"]["symptom"] == "Legacy issue evidence as plain text."
    assert repaired_issues["issues"][0]["resolution"]["summary"] == "Fixed manually."
    assert repaired_lessons["meta"]["generated_by"] == "esaa.project"
    assert repaired_lessons["meta"]["source_event_store"] == ".roadmap/activity.jsonl"
    assert repaired_lessons["lessons"][0]["status"] == "active"
    assert repaired_lessons["indexes"]["by_task_kind"] == {"impl": ["LES-0099"], "qa": ["LES-0099"]}
