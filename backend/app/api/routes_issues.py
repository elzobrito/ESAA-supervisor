from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from app.api.routes_projects import store
from app.api.schemas import IssueMutationResponse, IssueResolveRequest
from app.core.event_writer import EventWriter
from app.core.projector import Projector

router = APIRouter(prefix="/projects/{project_id}/issues", tags=["issues"])


def _get_project_roadmap_dir(project_id: str) -> str:
    if not store.active_project or store.active_project.id != project_id:
        raise HTTPException(status_code=404, detail="Project not active. Call GET /projects first.")
    return store.active_project.base_path


@router.post("/resolve", response_model=IssueMutationResponse)
async def resolve_issue(project_id: str, request: IssueResolveRequest):
    roadmap_dir = _get_project_roadmap_dir(project_id)
    issues_path = f"{roadmap_dir}/issues.json"

    with open(issues_path, "r", encoding="utf-8") as handle:
        issues_projection = json.load(handle)

    issue = next((item for item in issues_projection.get("issues", []) if item.get("issue_id") == request.issue_id), None)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found.")

    if issue.get("status") == "resolved":
        return IssueMutationResponse(
            issue_id=request.issue_id,
            status="resolved",
            message="Issue already resolved.",
        )

    resolution_summary = request.resolution_summary or "Issue resolved manually via supervisor UI after operational verification."
    payload = {
        "issue_id": request.issue_id,
        "task_id": issue.get("links", {}).get("fixes_task_id") or issue.get("links", {}).get("reported_by_task_id"),
        "resolution": {
            "summary": resolution_summary,
            "evidence": [
                "Resolved manually from the Issues page after operator review.",
            ],
        },
    }

    writer = EventWriter(roadmap_dir=roadmap_dir)
    event = writer.append_event(
        actor="orchestrator",
        action="issue.resolve",
        payload=payload,
    )
    Projector(roadmap_dir).sync_to_disk([event])

    return IssueMutationResponse(
        issue_id=request.issue_id,
        status="resolved",
        message="Issue resolved successfully.",
    )
