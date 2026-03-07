from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from app.utils.jsonl import append_jsonl, read_jsonl


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class EventWriter:
    roadmap_dir: str
    schema_version: str = "0.4.1"

    @property
    def activity_path(self) -> Path:
        return Path(self.roadmap_dir) / "activity.jsonl"

    def _load_events(self) -> list[dict[str, Any]]:
        if not self.activity_path.exists():
            return []
        return read_jsonl(str(self.activity_path))

    def next_event_seq(self) -> int:
        events = self._load_events()
        if not events:
            return 1
        return max(int(event["event_seq"]) for event in events) + 1

    @staticmethod
    def format_event_id(event_seq: int) -> str:
        return f"EV-{event_seq:08d}"

    def build_event(
        self,
        *,
        actor: str,
        action: str,
        payload: dict[str, Any],
        ts: str | None = None,
    ) -> dict[str, Any]:
        event_seq = self.next_event_seq()
        return {
            "schema_version": self.schema_version,
            "event_id": self.format_event_id(event_seq),
            "event_seq": event_seq,
            "ts": ts or utc_now_iso(),
            "actor": actor,
            "action": action,
            "payload": payload,
        }

    def append_event(
        self,
        *,
        actor: str,
        action: str,
        payload: dict[str, Any],
        ts: str | None = None,
    ) -> dict[str, Any]:
        event = self.build_event(actor=actor, action=action, payload=payload, ts=ts)
        append_jsonl(str(self.activity_path), event)
        return event

    def append_prebuilt(self, events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        written: list[dict[str, Any]] = []
        for event in events:
            append_jsonl(str(self.activity_path), event)
            written.append(event)
        return written

    def append_events(self, events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        next_seq = self.next_event_seq()
        written: list[dict[str, Any]] = []
        for event in events:
            built = {
                "schema_version": event.get("schema_version", self.schema_version),
                "event_id": self.format_event_id(next_seq),
                "event_seq": next_seq,
                "ts": event.get("ts", utc_now_iso()),
                "actor": event["actor"],
                "action": event["action"],
                "payload": event["payload"],
            }
            append_jsonl(str(self.activity_path), built)
            written.append(built)
            next_seq += 1
        return written

