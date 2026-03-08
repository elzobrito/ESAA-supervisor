from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.core.issues_sync import IssuesSync
from app.core.lessons_sync import LessonsSync
from app.utils.json_artifacts import load_json_artifact
from app.utils.jsonl import read_jsonl


class Projector:
    def __init__(self, roadmap_dir: str, roadmap_id: str = "roadmap.json"):
        self.roadmap_dir = Path(roadmap_dir)
        self.roadmap_id = roadmap_id
        self.issues_sync = IssuesSync()
        self.lessons_sync = LessonsSync()

    @property
    def roadmap_path(self) -> Path:
        return self.roadmap_dir / self.roadmap_id

    @property
    def issues_path(self) -> Path:
        return self.roadmap_dir / "issues.json"

    @property
    def lessons_path(self) -> Path:
        return self.roadmap_dir / "lessons.json"

    @property
    def activity_path(self) -> Path:
        return self.roadmap_dir / "activity.jsonl"

    def load_projection(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        roadmap = load_json_artifact(self.roadmap_path).payload
        issues = load_json_artifact(self.issues_path).payload
        lessons = load_json_artifact(self.lessons_path).payload
        return roadmap, issues, lessons

    def replay_activity(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        events = read_jsonl(str(self.activity_path))
        roadmap, issues, lessons = self.load_projection()
        return self.apply_events(roadmap, issues, lessons, events)

    def reconcile_activity_tail_to_disk(self) -> dict[str, Any]:
        roadmap, issues, lessons = self.load_projection()
        projected_seq = int(roadmap.get("meta", {}).get("run", {}).get("last_event_seq", 0) or 0)
        pending_events = [
            event
            for event in read_jsonl(str(self.activity_path))
            if int(event.get("event_seq", 0) or 0) > projected_seq
        ]

        if not pending_events:
            self._mark_integrity_status(roadmap, "ok", None)
            self._write_json(self.roadmap_path, roadmap)
            return {
                "applied_events": 0,
                "projected_event_seq": projected_seq,
                "is_consistent": True,
                "invalid_event": None,
            }

        valid_prefix: list[dict[str, Any]] = []
        trial_roadmap = deepcopy(roadmap)
        trial_issues = deepcopy(issues)
        trial_lessons = deepcopy(lessons)
        invalid_event: dict[str, Any] | None = None
        invalid_error: str | None = None

        for event in pending_events:
            try:
                self._apply_roadmap_event(trial_roadmap, event)
                self.issues_sync.apply_event(trial_issues, event)
                self.lessons_sync.apply_event(trial_lessons, event)
            except Exception as exc:
                invalid_event = event
                invalid_error = str(exc)
                break
            valid_prefix.append(event)

        if valid_prefix:
            roadmap, issues, lessons = self.apply_events(roadmap, issues, lessons, valid_prefix)

        if invalid_event is not None:
            self._mark_integrity_status(
                roadmap,
                "error",
                {
                    "message": invalid_error or "Invalid activity tail detected.",
                    "event_seq": invalid_event.get("event_seq"),
                    "event_id": invalid_event.get("event_id"),
                    "task_id": invalid_event.get("payload", {}).get("task_id"),
                    "actor": invalid_event.get("actor"),
                    "action": invalid_event.get("action"),
                },
            )
        else:
            self._mark_integrity_status(roadmap, "ok", None)

        self._write_json(self.roadmap_path, roadmap)
        self._write_json(self.issues_path, issues)
        self._write_json(self.lessons_path, lessons)
        return {
            "applied_events": len(valid_prefix),
            "projected_event_seq": roadmap["meta"]["run"]["last_event_seq"],
            "is_consistent": invalid_event is None,
            "invalid_event": None if invalid_event is None else {
                "event_seq": invalid_event.get("event_seq"),
                "event_id": invalid_event.get("event_id"),
                "task_id": invalid_event.get("payload", {}).get("task_id"),
                "actor": invalid_event.get("actor"),
                "action": invalid_event.get("action"),
                "message": invalid_error or "Invalid activity tail detected.",
            },
        }

    def apply_events(
        self,
        roadmap: dict[str, Any],
        issues: dict[str, Any],
        lessons: dict[str, Any],
        events: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        projected_roadmap = deepcopy(roadmap)
        projected_issues = deepcopy(issues)
        projected_lessons = deepcopy(lessons)

        for event in events:
            self._apply_roadmap_event(projected_roadmap, event)
            self.issues_sync.apply_event(projected_issues, event)
            self.lessons_sync.apply_event(projected_lessons, event)

        last_event_seq = max((event["event_seq"] for event in events), default=projected_roadmap["meta"]["run"]["last_event_seq"])
        updated_at = events[-1]["ts"] if events else projected_roadmap["meta"]["updated_at"]

        self._sync_roadmap(projected_roadmap, last_event_seq=last_event_seq, updated_at=updated_at)
        projected_issues = self.issues_sync.sync_projection(projected_issues, last_event_seq=last_event_seq, updated_at=updated_at)
        projected_lessons = self.lessons_sync.sync_projection(projected_lessons, updated_at=updated_at)
        return projected_roadmap, projected_issues, projected_lessons

    def sync_to_disk(self, events: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        roadmap, issues, lessons = self.load_projection()
        projected_roadmap, projected_issues, projected_lessons = self.apply_events(roadmap, issues, lessons, events)
        self._write_json(self.roadmap_path, projected_roadmap)
        self._write_json(self.issues_path, projected_issues)
        self._write_json(self.lessons_path, projected_lessons)
        return projected_roadmap, projected_issues, projected_lessons

    def _apply_roadmap_event(self, roadmap: dict[str, Any], event: dict[str, Any]) -> None:
        action = event["action"]
        payload = event["payload"]

        if action == "claim":
            task = self._find_task(roadmap, payload["task_id"])
            self._expect_status(task, "todo")
            task["status"] = "in_progress"
            task["assigned_to"] = event["actor"]
            task["started_at"] = event["ts"]
            return

        if action == "complete":
            task = self._find_task(roadmap, payload["task_id"])
            if task.get("status") in {"review", "done"}:
                if task.get("assigned_to") and task["assigned_to"] != event["actor"]:
                    raise ValueError(f"Task {task['task_id']} assigned to {task['assigned_to']}, not {event['actor']}")
                return
            self._expect_status(task, "in_progress")
            if task.get("assigned_to") and task["assigned_to"] != event["actor"]:
                raise ValueError(f"Task {task['task_id']} assigned to {task['assigned_to']}, not {event['actor']}")
            task["status"] = "review"
            task["verification"] = payload.get("verification", {})
            task["completed_at"] = event["ts"]
            if "issue_id" in payload:
                task["issue_id"] = payload["issue_id"]
            if "fixes" in payload:
                task["fixes"] = payload["fixes"]
            return

        if action == "review":
            task = self._find_task(roadmap, payload["task_id"])
            decision = payload["decision"]
            if decision == "approve" and task.get("status") == "done":
                return
            self._expect_status(task, "review")
            if decision == "approve":
                task["status"] = "done"
            elif decision == "request_changes":
                task["status"] = "in_progress"
                task.pop("completed_at", None)
            else:
                raise ValueError(f"Unsupported review decision: {decision}")
            return

        if action == "orchestrator.view.mutate":
            transition = payload.get("transition")
            task_id = payload.get("task_id")
            if not task_id:
                return
            task = self._find_task(roadmap, task_id)
            if transition:
                _, new_status = transition.split("->", 1)
                task["status"] = new_status
                if "assigned_to" in payload:
                    task["assigned_to"] = payload["assigned_to"]
                if "started_at" in payload:
                    task["started_at"] = payload["started_at"]
                if "completed_at" in payload:
                    task["completed_at"] = payload["completed_at"]
                if "verification" in payload:
                    task["verification"] = payload["verification"]
                for field in payload.get("clear_fields", []):
                    task.pop(field, None)
            if "planning" in payload and isinstance(payload["planning"], dict):
                current_planning = task.get("planning", {}) if isinstance(task.get("planning"), dict) else {}
                task["planning"] = {**current_planning, **payload["planning"]}
            return

    def _sync_roadmap(self, roadmap: dict[str, Any], *, last_event_seq: int, updated_at: str) -> None:
        roadmap["meta"]["run"]["last_event_seq"] = last_event_seq
        roadmap["meta"]["updated_at"] = updated_at
        roadmap["indexes"]["by_status"] = self._count_by_status(roadmap["tasks"])
        roadmap["indexes"]["by_kind"] = self._count_by_kind(roadmap["tasks"])
        roadmap["indexes"]["by_preferred_runner"] = self._group_by_preferred_runner(roadmap["tasks"])
        roadmap["meta"]["run"]["projection_hash_sha256"] = self.compute_projection_hash(roadmap)
        roadmap["meta"]["run"]["verify_status"] = "ok"
        roadmap["meta"]["run"].pop("integrity_error", None)

    @staticmethod
    def _mark_integrity_status(roadmap: dict[str, Any], verify_status: str, integrity_error: dict[str, Any] | None) -> None:
        roadmap.setdefault("meta", {}).setdefault("run", {})
        roadmap["meta"]["run"]["verify_status"] = verify_status
        roadmap["meta"]["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        if integrity_error:
            roadmap["meta"]["run"]["integrity_error"] = integrity_error
        else:
            roadmap["meta"]["run"].pop("integrity_error", None)

    @staticmethod
    def compute_projection_hash(roadmap: dict[str, Any]) -> str:
        payload = {
            "schema_version": roadmap["meta"]["schema_version"],
            "project": roadmap["project"],
            "tasks": roadmap["tasks"],
            "indexes": roadmap["indexes"],
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _count_by_status(tasks: list[dict[str, Any]]) -> dict[str, int]:
        counts = {"todo": 0, "in_progress": 0, "review": 0, "done": 0}
        for task in tasks:
            counts[task["status"]] = counts.get(task["status"], 0) + 1
        return counts

    @staticmethod
    def _count_by_kind(tasks: list[dict[str, Any]]) -> dict[str, int]:
        counts = {"spec": 0, "impl": 0, "qa": 0}
        for task in tasks:
            counts[task["task_kind"]] = counts.get(task["task_kind"], 0) + 1
        return counts

    @staticmethod
    def _group_by_preferred_runner(tasks: list[dict[str, Any]]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for task in tasks:
            planning = task.get("planning", {})
            if not isinstance(planning, dict):
                continue
            preferred_runner = planning.get("preferred_runner")
            if not isinstance(preferred_runner, str) or not preferred_runner:
                continue
            grouped.setdefault(preferred_runner, []).append(task["task_id"])
        return grouped

    @staticmethod
    def _find_task(roadmap: dict[str, Any], task_id: str) -> dict[str, Any]:
        for task in roadmap.get("tasks", []):
            if task["task_id"] == task_id:
                return task
        raise KeyError(f"Task not found: {task_id}")

    @staticmethod
    def _expect_status(task: dict[str, Any], expected: str) -> None:
        current = task["status"]
        if current != expected:
            raise ValueError(f"Task {task['task_id']} expected status {expected}, got {current}")

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
