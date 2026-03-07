from __future__ import annotations

from copy import deepcopy
from typing import Any


class IssuesSync:
    def apply_event(self, projection: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        action = event["action"]
        if action == "issue.report":
            self._apply_issue_report(projection, event)
        elif action == "issue.resolve":
            self._apply_issue_resolve(projection, event)
        elif action == "complete":
            self._apply_complete_resolution(projection, event)
        return projection

    def sync_projection(
        self,
        projection: dict[str, Any],
        *,
        last_event_seq: int | None = None,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        synced = deepcopy(projection)
        if last_event_seq is not None:
            synced.setdefault("meta", {})["last_event_seq"] = last_event_seq
        if updated_at is not None:
            synced.setdefault("meta", {})["updated_at"] = updated_at
        synced.setdefault("indexes", {})["open_by_baseline"] = self._build_open_by_baseline(synced.get("issues", []))
        return synced

    @staticmethod
    def _find_issue(projection: dict[str, Any], issue_id: str) -> dict[str, Any] | None:
        for issue in projection.get("issues", []):
            if issue.get("issue_id") == issue_id:
                return issue
        return None

    def _apply_issue_report(self, projection: dict[str, Any], event: dict[str, Any]) -> None:
        payload = event["payload"]
        issue = self._find_issue(projection, payload["issue_id"])
        if issue is None:
            projection.setdefault("issues", []).append(
                {
                    "issue_id": payload["issue_id"],
                    "status": "open",
                    "severity": payload["severity"],
                    "title": payload["title"],
                    "baseline_id": payload.get("baseline_id"),
                    "affected": payload.get("affected", {}),
                    "evidence": payload["evidence"],
                    "resolution": None,
                    "links": {
                        "reported_by_task_id": payload.get("task_id"),
                        "fixes_task_id": None,
                        "hotfix_task_id": payload.get("hotfix_task_id"),
                    },
                    "timeline": {
                        "created_event_seq": event["event_seq"],
                        "resolved_event_seq": None,
                    },
                }
            )
            return

        issue["status"] = "open"
        issue["severity"] = payload.get("severity", issue["severity"])
        issue["title"] = payload.get("title", issue["title"])
        issue["affected"] = payload.get("affected", issue.get("affected", {}))
        issue["evidence"] = payload.get("evidence", issue["evidence"])
        issue["resolution"] = None
        issue["timeline"]["resolved_event_seq"] = None

    def _apply_issue_resolve(self, projection: dict[str, Any], event: dict[str, Any]) -> None:
        payload = event["payload"]
        issue = self._find_issue(projection, payload["issue_id"])
        if issue is None:
            return
        issue["status"] = "resolved"
        issue["resolution"] = payload.get("resolution")
        issue["links"]["fixes_task_id"] = payload.get("task_id", issue["links"].get("fixes_task_id"))
        issue["timeline"]["resolved_event_seq"] = event["event_seq"]

    def _apply_complete_resolution(self, projection: dict[str, Any], event: dict[str, Any]) -> None:
        payload = event["payload"]
        issue_id = payload.get("issue_id")
        fixes = payload.get("fixes")
        if not issue_id or not fixes:
            return
        issue = self._find_issue(projection, issue_id)
        if issue is None:
            return
        issue["status"] = "resolved"
        issue["resolution"] = {
            "summary": fixes,
            "evidence": payload.get("verification", {}).get("checks", []),
        }
        issue["links"]["fixes_task_id"] = payload.get("task_id")
        issue["timeline"]["resolved_event_seq"] = event["event_seq"]

    @staticmethod
    def _build_open_by_baseline(issues: list[dict[str, Any]]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for issue in issues:
            if issue.get("status") != "open":
                continue
            baseline_id = issue.get("baseline_id")
            if not baseline_id:
                continue
            grouped.setdefault(baseline_id, []).append(issue["issue_id"])
        return grouped

