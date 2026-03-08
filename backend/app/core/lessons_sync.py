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
        synced["schema_version"] = "0.4.0"
        synced["lessons"] = [self._normalize_lesson(lesson) for lesson in synced.get("lessons", [])]
        meta = synced.setdefault("meta", {})
        meta.setdefault("schema_version", "0.4.0")
        meta.setdefault("esaa_version", "0.4.x")
        meta.setdefault("generated_by", "esaa.project")
        meta.setdefault("source_event_store", ".roadmap/activity.jsonl")
        if updated_at is not None:
            meta["updated_at"] = updated_at
        else:
            meta.setdefault("updated_at", "")
        synced.setdefault("indexes", {})["by_task_kind"] = self._by_task_kind(synced.get("lessons", []))
        synced.setdefault("indexes", {})["by_enforcement_applies_to"] = self._by_enforcement(synced.get("lessons", []))
        return synced

    @staticmethod
    def _normalize_lesson(lesson: dict[str, Any]) -> dict[str, Any]:
        normalized = deepcopy(lesson)
        normalized.setdefault("status", "active")
        normalized.setdefault("created_at", "")
        normalized.setdefault("source_refs", [])
        scope = normalized.get("scope")
        if not isinstance(scope, dict):
            scope = {}
        task_kinds = scope.get("task_kinds")
        if not isinstance(task_kinds, list):
            task_kinds = []
        scope["task_kinds"] = [item for item in task_kinds if isinstance(item, str)]
        normalized["scope"] = scope
        enforcement = normalized.get("enforcement")
        if not isinstance(enforcement, dict):
            enforcement = {}
        enforcement.setdefault("mode", "warn")
        enforcement.setdefault("applies_to", "workflow_gate")
        normalized["enforcement"] = enforcement
        return normalized

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
