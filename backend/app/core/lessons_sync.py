from __future__ import annotations

from copy import deepcopy
from typing import Any


class LessonsSync:
    def apply_event(self, projection: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        if event["action"] not in {"lesson", "lesson.learn", "lesson.record"}:
            return projection

        payload = event["payload"]
        lesson = self._find_lesson(projection, payload["lesson_id"])
        lesson_payload = {
            "lesson_id": payload["lesson_id"],
            "status": payload.get("status", "active"),
            "created_at": payload.get("created_at", event["ts"]),
            "title": payload["title"],
            "mistake": payload["mistake"],
            "rule": payload["rule"],
            "scope": payload["scope"],
            "enforcement": payload["enforcement"],
            "source_refs": payload.get("source_refs", []),
        }

        if lesson is None:
            projection.setdefault("lessons", []).append(lesson_payload)
        else:
            lesson.update(lesson_payload)
        return projection

    def sync_projection(self, projection: dict[str, Any], *, updated_at: str | None = None) -> dict[str, Any]:
        synced = deepcopy(projection)
        if updated_at is not None:
            synced.setdefault("meta", {})["updated_at"] = updated_at
        synced.setdefault("indexes", {})["by_task_kind"] = self._by_task_kind(synced.get("lessons", []))
        synced.setdefault("indexes", {})["by_enforcement_applies_to"] = self._by_enforcement(synced.get("lessons", []))
        return synced

    @staticmethod
    def _find_lesson(projection: dict[str, Any], lesson_id: str) -> dict[str, Any] | None:
        for lesson in projection.get("lessons", []):
            if lesson.get("lesson_id") == lesson_id:
                return lesson
        return None

    @staticmethod
    def _by_task_kind(lessons: list[dict[str, Any]]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for lesson in lessons:
            for task_kind in lesson.get("scope", {}).get("task_kinds", []):
                grouped.setdefault(task_kind, []).append(lesson["lesson_id"])
        return grouped

    @staticmethod
    def _by_enforcement(lessons: list[dict[str, Any]]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for lesson in lessons:
            applies_to = lesson.get("enforcement", {}).get("applies_to")
            if applies_to:
                grouped.setdefault(applies_to, []).append(lesson["lesson_id"])
        return grouped

