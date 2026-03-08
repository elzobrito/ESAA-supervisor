import json
from pathlib import Path

from app.core.canonical_store import CanonicalStore


def test_state_consistency_follows_roadmap_hash_status(tmp_path: Path) -> None:
    roadmap_dir = tmp_path / ".roadmap"
    roadmap_dir.mkdir()
    (roadmap_dir / "activity.jsonl").write_text("", encoding="utf-8")
    (roadmap_dir / "issues.json").write_text(json.dumps({"issues": []}), encoding="utf-8")
    (roadmap_dir / "lessons.json").write_text(json.dumps({"lessons": []}), encoding="utf-8")
    (roadmap_dir / "roadmap.json").write_text(
        json.dumps(
            {
                "meta": {
                    "schema_version": "0.4.0",
                    "run": {
                        "last_event_seq": 0,
                        "projection_hash_sha256": "0000",
                        "verify_status": "mismatch",
                    },
                },
                "project": {"name": "demo"},
                "tasks": [],
                "indexes": {"by_status": {"todo": 0, "in_progress": 0, "review": 0, "done": 0}},
            }
        ),
        encoding="utf-8",
    )

    store = CanonicalStore(str(tmp_path))
    store.load_project("demo", str(roadmap_dir))

    state = store.get_state()

    assert state.is_consistent is False


def test_state_activity_tolerates_invalid_utf8_jsonl(tmp_path: Path) -> None:
    roadmap_dir = tmp_path / ".roadmap"
    roadmap_dir.mkdir()
    (roadmap_dir / "issues.json").write_text(json.dumps({"issues": []}), encoding="utf-8")
    (roadmap_dir / "lessons.json").write_text(json.dumps({"lessons": []}), encoding="utf-8")
    (roadmap_dir / "roadmap.json").write_text(
        json.dumps(
            {
                "meta": {
                    "schema_version": "0.4.0",
                    "run": {
                        "last_event_seq": 2,
                        "projection_hash_sha256": "0000",
                        "verify_status": "ok",
                    },
                },
                "project": {"name": "demo"},
                "tasks": [],
                "indexes": {"by_status": {"todo": 0, "in_progress": 0, "review": 0, "done": 0}},
            }
        ),
        encoding="utf-8",
    )
    valid_line = json.dumps(
        {
            "schema_version": "0.4.1",
            "event_id": "EV-00000001",
            "event_seq": 1,
            "ts": "2026-03-07T00:00:00Z",
            "actor": "orchestrator",
            "action": "verify.ok",
            "payload": {},
        }
    ).encode("utf-8")
    invalid_utf8_line = b'{"schema_version":"0.4.1","event_id":"EV-00000002","event_seq":2,"ts":"2026-03-07T00:00:01Z","actor":"codex","action":"complete","payload":{"message":"broken \xed entry"}}'
    (roadmap_dir / "activity.jsonl").write_bytes(valid_line + b"\n" + invalid_utf8_line + b"\n")

    store = CanonicalStore(str(tmp_path))
    store.load_project("demo", str(roadmap_dir))

    state = store.get_state()

    assert len(state.activity) == 2
    assert state.activity[-1]["event_seq"] == 2
