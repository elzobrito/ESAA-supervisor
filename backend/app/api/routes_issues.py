from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.routes_projects import store
from app.api.routes_state import _discover_roadmap_variants
from app.api.schemas import IssueMutationResponse, IssueResolveRequest
from app.core.event_writer import EventWriter
from app.core.projector import Projector
from app.utils.json_artifacts import JsonArtifactLoadError, load_json_artifact

router = APIRouter(prefix="/projects/{project_id}/issues", tags=["issues"])


def _get_project_roadmap_dir(project_id: str) -> str:
    if not store.active_project or store.active_project.id != project_id:
        raise HTTPException(status_code=404, detail="Project not active. Call GET /projects first.")
    return store.active_project.base_path


def _sync_event_to_roadmap_variants(roadmap_dir: str, event: dict[str, object]) -> None:
    variants = _discover_roadmap_variants(roadmap_dir)
    synced = False

    for roadmap_id, candidate in variants.items():
        if candidate.get("payload") is None:
            continue
        Projector(roadmap_dir, roadmap_id=roadmap_id).sync_to_disk([event])
        synced = True

    if not synced:
        Projector(roadmap_dir).sync_to_disk([event])


@router.post("/resolve", response_model=IssueMutationResponse)
async def resolve_issue(project_id: str, request: IssueResolveRequest):
    roadmap_dir = _get_project_roadmap_dir(project_id)
    issues_path = f"{roadmap_dir}/issues.json"

    try:
        issues_projection = load_json_artifact(issues_path).payload
    except JsonArtifactLoadError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

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
    task_id = (
        issue.get("links", {}).get("fixes_task_id")
        or issue.get("links", {}).get("reported_by_task_id")
        or issue.get("resolved_by_task_id")
        or issue.get("task_id")
    )
    payload = {
        "issue_id": request.issue_id,
        "task_id": task_id,
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
    _sync_event_to_roadmap_variants(roadmap_dir, event)

    return IssueMutationResponse(
        issue_id=request.issue_id,
        status="resolved",
        message="Issue resolved successfully.",
    )
