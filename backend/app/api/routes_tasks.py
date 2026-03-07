from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.routes_projects import store
from app.api.routes_state import _load_roadmap_variants
from app.api.schemas import TaskMutationResponse, TaskResetRequest, TaskReviewRequest
from app.core.event_writer import EventWriter, utc_now_iso
from app.core.projector import Projector

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])


def _get_project_roadmap_dir(project_id: str) -> str:
    if not store.active_project or store.active_project.id != project_id:
        raise HTTPException(status_code=404, detail="Project not active. Call GET /projects first.")
    return store.active_project.base_path


@router.post("/reset", response_model=TaskMutationResponse)
async def reset_task_to_todo(project_id: str, request: TaskResetRequest):
    roadmap_dir = _get_project_roadmap_dir(project_id)
    roadmap_id = request.roadmap_id or "roadmap.json"
    variants = _load_roadmap_variants(roadmap_dir)
    roadmap = variants.get(roadmap_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Requested roadmap not found.")

    task = next((item for item in roadmap.get("tasks", []) if item.get("task_id") == request.task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    if task.get("status") == "todo":
        return TaskMutationResponse(
            task_id=request.task_id,
            roadmap_id=roadmap_id,
            status="todo",
            message="Task already in todo.",
        )

    payload = {
        "task_id": request.task_id,
        "transition": f"{task.get('status', 'unknown')}->todo",
        "assigned_to": None,
        "started_at": None,
        "completed_at": None,
        "verification": {},
        "clear_fields": ["issue_id", "fixes"],
    }
    writer = EventWriter(roadmap_dir=roadmap_dir)
    event = writer.append_event(
        actor="orchestrator",
        action="orchestrator.view.mutate",
        payload=payload,
    )
    Projector(roadmap_dir, roadmap_id=roadmap_id).sync_to_disk([event])

    return TaskMutationResponse(
        task_id=request.task_id,
        roadmap_id=roadmap_id,
        status="todo",
        message="Task regressed to todo.",
    )


@router.post("/{task_id}/review", response_model=TaskMutationResponse)
async def review_task(project_id: str, task_id: str, request: TaskReviewRequest):
    roadmap_dir = _get_project_roadmap_dir(project_id)
    roadmap_id = request.roadmap_id or "roadmap.json"
    variants = _load_roadmap_variants(roadmap_dir)
    roadmap = variants.get(roadmap_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Requested roadmap not found.")

    task = next((item for item in roadmap.get("tasks", []) if item.get("task_id") == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    if task.get("status") != "review":
        raise HTTPException(status_code=409, detail=f"Task is in status {task.get('status')}, expected review.")

    if request.decision == "approve":
        target_status = "done"
        payload = {
            "task_id": task_id,
            "transition": "review->done",
            "completed_at": utc_now_iso(),
        }
    elif request.decision == "reject":
        target_status = "todo"
        payload = {
            "task_id": task_id,
            "transition": "review->todo",
            "assigned_to": None,
            "started_at": None,
            "completed_at": None,
            "verification": {},
            "clear_fields": ["issue_id", "fixes"],
        }
    else:
        raise HTTPException(status_code=422, detail="Decision must be 'approve' or 'reject'")

    writer = EventWriter(roadmap_dir=roadmap_dir)
    event = writer.append_event(
        actor="orchestrator",
        action="orchestrator.view.mutate",
        payload=payload,
    )
    Projector(roadmap_dir, roadmap_id=roadmap_id).sync_to_disk([event])

    return TaskMutationResponse(
        task_id=task_id,
        roadmap_id=roadmap_id,
        status=target_status,
        message=f"Task reviewed with decision: {request.decision}",
    )
