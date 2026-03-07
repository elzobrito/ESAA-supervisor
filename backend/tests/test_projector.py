import json
from pathlib import Path

from app.core.projector import Projector


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_projector_applies_claim_complete_review_and_issue_resolution(tmp_path: Path) -> None:
    roadmap_dir = tmp_path
    _write_json(
        roadmap_dir / "roadmap.json",
        {
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
            "tasks": [
                {
                    "task_id": "ESUP-IMPL-009",
                    "task_kind": "impl",
                    "title": "Writer",
                    "description": "desc",
                    "status": "todo",
                    "depends_on": [],
                    "targets": ["backend/app/core/"],
                    "outputs": {"files": ["backend/app/core/event_writer.py"]},
                    "immutability": {"done_is_immutable": True},
                    "required_verification": ["ok"],
                }
            ],
            "indexes": {
                "by_status": {"todo": 1, "in_progress": 0, "review": 0, "done": 0},
                "by_kind": {"spec": 0, "impl": 1, "qa": 0},
            },
        },
    )
    _write_json(
        roadmap_dir / "issues.json",
        {
            "meta": {
                "schema_version": "0.4.0",
                "esaa_version": "0.4.x",
                "generated_by": "esaa.project",
                "source_event_store": ".roadmap/activity.jsonl",
                "last_event_seq": 0,
                "updated_at": "2026-03-07T00:00:00Z",
            },
            "issues": [
                {
                    "issue_id": "ISS-0001",
                    "status": "open",
                    "severity": "medium",
                    "title": "Gap",
                    "baseline_id": None,
                    "affected": {},
                    "evidence": {"symptom": "gap", "repro_steps": ["step"]},
                    "resolution": None,
                    "links": {"reported_by_task_id": "ESUP-IMPL-009", "fixes_task_id": None, "hotfix_task_id": None},
                    "timeline": {"created_event_seq": 1, "resolved_event_seq": None},
                }
            ],
            "indexes": {"open_by_baseline": {}},
        },
    )
    _write_json(
        roadmap_dir / "lessons.json",
        {
            "meta": {
                "schema_version": "0.4.0",
                "esaa_version": "0.4.x",
                "generated_by": "esaa.project",
                "source_event_store": ".roadmap/activity.jsonl",
                "updated_at": "2026-03-07T00:00:00Z",
            },
            "lessons": [],
            "indexes": {"by_task_kind": {}, "by_enforcement_applies_to": {}},
        },
    )

    projector = Projector(str(roadmap_dir))
    roadmap, issues, lessons = projector.apply_events(
        json.loads((roadmap_dir / "roadmap.json").read_text(encoding="utf-8")),
        json.loads((roadmap_dir / "issues.json").read_text(encoding="utf-8")),
        json.loads((roadmap_dir / "lessons.json").read_text(encoding="utf-8")),
        [
            {
                "schema_version": "0.4.1",
                "event_id": "EV-00000010",
                "event_seq": 10,
                "ts": "2026-03-07T00:00:10Z",
                "actor": "agent-impl",
                "action": "claim",
                "payload": {"task_id": "ESUP-IMPL-009", "prior_status": "todo"},
            },
            {
                "schema_version": "0.4.1",
                "event_id": "EV-00000011",
                "event_seq": 11,
                "ts": "2026-03-07T00:00:20Z",
                "actor": "agent-impl",
                "action": "complete",
                "payload": {
                    "task_id": "ESUP-IMPL-009",
                    "prior_status": "in_progress",
                    "issue_id": "ISS-0001",
                    "fixes": "writer implemented",
                    "verification": {"checks": ["append ok"]},
                },
            },
            {
                "schema_version": "0.4.1",
                "event_id": "EV-00000012",
                "event_seq": 12,
                "ts": "2026-03-07T00:00:30Z",
                "actor": "agent-qa",
                "action": "review",
                "payload": {"task_id": "ESUP-IMPL-009", "prior_status": "review", "decision": "approve", "tasks": ["ok"]},
            },
        ],
    )

    task = roadmap["tasks"][0]
    assert task["status"] == "done"
    assert task["assigned_to"] == "agent-impl"
    assert task["verification"]["checks"] == ["append ok"]
    assert issues["issues"][0]["status"] == "resolved"
    assert issues["issues"][0]["timeline"]["resolved_event_seq"] == 11
    assert roadmap["indexes"]["by_status"]["done"] == 1
    assert len(roadmap["meta"]["run"]["projection_hash_sha256"]) == 64
    assert lessons["indexes"]["by_task_kind"] == {}
