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
        synced["schema_version"] = "0.4.0"
        synced["issues"] = [self._normalize_issue(issue) for issue in synced.get("issues", [])]
        meta = synced.setdefault("meta", {})
        meta.setdefault("schema_version", "0.4.0")
        meta.setdefault("esaa_version", "0.4.x")
        meta.setdefault("generated_by", "esaa.project")
        meta.setdefault("source_event_store", ".roadmap/activity.jsonl")
        if last_event_seq is not None:
            meta["last_event_seq"] = last_event_seq
        else:
            meta.setdefault("last_event_seq", 0)
        if updated_at is not None:
            meta["updated_at"] = updated_at
        else:
            meta.setdefault("updated_at", "")
        synced.setdefault("indexes", {})["open_by_baseline"] = self._build_open_by_baseline(synced.get("issues", []))
        return synced

    @staticmethod
    def _normalize_issue(issue: dict[str, Any]) -> dict[str, Any]:
        links = issue.get("links")
        if not isinstance(links, dict):
            links = {}
        affected = issue.get("affected")
        if not isinstance(affected, dict):
            affected = {}
        timeline = issue.get("timeline")
        if not isinstance(timeline, dict):
            timeline = {}
        evidence = IssuesSync._normalize_evidence(issue.get("evidence"))
        resolution = IssuesSync._normalize_resolution(issue.get("resolution"))

        task_id = issue.get("task_id") or affected.get("task_id") or links.get("reported_by_task_id")
        if task_id and not affected.get("task_id"):
            affected["task_id"] = task_id
        if task_id and not links.get("reported_by_task_id"):
            links["reported_by_task_id"] = task_id
        if "fixes_task_id" not in links:
            links["fixes_task_id"] = issue.get("resolved_by_task_id")
        if "hotfix_task_id" not in links:
            links["hotfix_task_id"] = None
        if "created_event_seq" not in timeline:
            timeline["created_event_seq"] = None
        if "resolved_event_seq" not in timeline:
            timeline["resolved_event_seq"] = None

        issue["affected"] = affected
        issue["links"] = links
        issue["timeline"] = timeline
        issue["evidence"] = evidence
        issue["resolution"] = resolution
        issue.setdefault("baseline_id", None)
        issue.setdefault("reported_at", None)
        issue.setdefault("resolved_at", None)
        if not issue.get("task_id"):
            issue["task_id"] = task_id
        if issue.get("resolved_by_task_id") is None and links.get("fixes_task_id") is not None:
            issue["resolved_by_task_id"] = links["fixes_task_id"]
        return issue

    @staticmethod
    def _normalize_evidence(evidence: Any) -> dict[str, Any]:
        if isinstance(evidence, str):
            return {
                "symptom": evidence,
                "repro_steps": ["Consultar activity.jsonl para o evento original do issue."],
            }
        if isinstance(evidence, dict):
            symptom = evidence.get("symptom")
            if not isinstance(symptom, str) or not symptom.strip():
                symptom = str(symptom) if symptom is not None else "Issue registrado sem symptom estruturado."
            repro_steps = evidence.get("repro_steps")
            if isinstance(repro_steps, str):
                repro_steps = [repro_steps]
            elif not isinstance(repro_steps, list):
                repro_steps = []
            repro_steps = [step for step in repro_steps if isinstance(step, str) and step.strip()]
            if not repro_steps:
                repro_steps = ["Consultar activity.jsonl para o evento original do issue."]
            return {
                "symptom": symptom,
                "repro_steps": repro_steps,
            }
        return {
            "symptom": "Issue registrado sem evidência estruturada.",
            "repro_steps": ["Consultar activity.jsonl para o evento original do issue."],
        }

    @staticmethod
    def _normalize_resolution(resolution: Any) -> dict[str, Any] | None:
        if resolution is None:
            return None
        if isinstance(resolution, str):
            return {
                "summary": resolution,
                "evidence": [],
            }
        if isinstance(resolution, dict):
            summary = resolution.get("summary")
            if not isinstance(summary, str):
                summary = str(summary) if summary is not None else ""
            evidence = resolution.get("evidence")
            if isinstance(evidence, str):
                evidence = [evidence]
            elif not isinstance(evidence, list):
                evidence = []
            evidence = [item for item in evidence if isinstance(item, str)]
            return {
                "summary": summary,
                "evidence": evidence,
            }
        return {
            "summary": "Issue resolvido sem detalhamento estruturado.",
            "evidence": [],
        }

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
                self._normalize_issue(
                    {
                        "issue_id": payload["issue_id"],
                        "status": "open",
                        "severity": payload["severity"],
                        "title": payload["title"],
                        "baseline_id": payload.get("baseline_id"),
                        "affected": payload.get("affected", {}),
                        "evidence": payload["evidence"],
                        "resolution": None,
                        "task_id": payload.get("task_id"),
                        "reported_at": event["ts"],
                        "resolved_at": None,
                        "resolved_by_task_id": None,
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
            )
            return

        issue = self._normalize_issue(issue)
        issue["status"] = "open"
        issue["severity"] = payload.get("severity", issue["severity"])
        issue["title"] = payload.get("title", issue["title"])
        issue["affected"] = payload.get("affected", issue.get("affected", {}))
        issue["evidence"] = payload.get("evidence", issue["evidence"])
        issue["resolution"] = None
        issue["task_id"] = payload.get("task_id", issue.get("task_id"))
        issue["resolved_at"] = None
        issue["resolved_by_task_id"] = None
        if issue["task_id"] and not issue["affected"].get("task_id"):
            issue["affected"]["task_id"] = issue["task_id"]
        issue["links"]["reported_by_task_id"] = payload.get("task_id", issue["links"].get("reported_by_task_id"))
        issue["links"]["hotfix_task_id"] = payload.get("hotfix_task_id", issue["links"].get("hotfix_task_id"))
        issue["links"]["fixes_task_id"] = None
        issue["timeline"]["resolved_event_seq"] = None

    def _apply_issue_resolve(self, projection: dict[str, Any], event: dict[str, Any]) -> None:
        payload = event["payload"]
        issue = self._find_issue(projection, payload["issue_id"])
        if issue is None:
            return
        issue = self._normalize_issue(issue)
        issue["status"] = "resolved"
        issue["resolution"] = payload.get("resolution", issue.get("resolution"))
        links = issue.setdefault("links", {})
        links["fixes_task_id"] = payload.get("task_id") or links.get("fixes_task_id") or issue.get("task_id")
        issue["resolved_by_task_id"] = links.get("fixes_task_id")
        issue["resolved_at"] = event["ts"]
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
        issue = self._normalize_issue(issue)
        issue["status"] = "resolved"
        issue["resolution"] = {
            "summary": fixes,
            "evidence": payload.get("verification", {}).get("checks", []),
        }
        issue["links"]["fixes_task_id"] = payload.get("task_id") or issue["links"].get("fixes_task_id") or issue.get("task_id")
        issue["resolved_by_task_id"] = issue["links"]["fixes_task_id"]
        issue["resolved_at"] = event["ts"]
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
