import json
from pathlib import Path

from app.core.event_writer import EventWriter
from app.utils.jsonl import read_jsonl


def test_append_events_uses_next_monotonic_sequence(tmp_path: Path) -> None:
    roadmap_dir = tmp_path
    activity_path = roadmap_dir / "activity.jsonl"
    activity_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "schema_version": "0.4.1",
                        "event_id": "EV-00000001",
                        "event_seq": 1,
                        "ts": "2026-03-07T00:00:00Z",
                        "actor": "orchestrator",
                        "action": "verify.ok",
                        "payload": {},
                    }
                ),
                json.dumps(
                    {
                        "schema_version": "0.4.1",
                        "event_id": "EV-00000004",
                        "event_seq": 4,
                        "ts": "2026-03-07T00:00:03Z",
                        "actor": "orchestrator",
                        "action": "verify.ok",
                        "payload": {},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    writer = EventWriter(str(roadmap_dir))
    written = writer.append_events(
        [
            {"actor": "agent-impl", "action": "claim", "payload": {"task_id": "ESUP-IMPL-009", "prior_status": "todo"}, "ts": "2026-03-07T00:00:10Z"},
            {"actor": "orchestrator", "action": "verify.start", "payload": {"strict": True}, "ts": "2026-03-07T00:00:11Z"},
        ]
    )

    assert [event["event_seq"] for event in written] == [5, 6]
    assert [event["event_id"] for event in written] == ["EV-00000005", "EV-00000006"]
    lines = activity_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 4


def test_read_jsonl_tolerates_invalid_utf8_line(tmp_path: Path) -> None:
    activity_path = tmp_path / "activity.jsonl"
    valid_line = json.dumps(
        {
            "schema_version": "0.4.1",
            "event_id": "EV-00000001",
            "event_seq": 1,
            "ts": "2026-03-07T00:00:00Z",
            "actor": "orchestrator",
            "action": "verify.ok",
            "payload": {"message": "ok"},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    corrupted_line = b'{"schema_version":"0.4.1","event_id":"EV-00000002","event_seq":2,"ts":"2026-03-07T00:00:01Z","actor":"codex","action":"complete","payload":{"message":"bad \xed line"}}'
    activity_path.write_bytes(valid_line + b"\n" + corrupted_line + b"\n")

    rows = read_jsonl(str(activity_path))

    assert len(rows) == 2
    assert rows[0]["event_seq"] == 1
    assert rows[1]["event_seq"] == 2
