from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.routes_projects import store
from app.api.routes_state import _discover_roadmap_variants
from app.api.schemas import TaskMutationResponse, TaskPlanningMutationResponse, TaskPlanningUpdateRequest, TaskResetRequest, TaskReviewRequest
from app.core.agent_router import AgentRouter
from app.core.event_writer import EventWriter, utc_now_iso
from app.core.projector import Projector
from app.core.run_coordinator import RunCoordinator

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])


def _get_project_roadmap_dir(project_id: str) -> str:
    if not store.active_project or store.active_project.id != project_id:
        raise HTTPException(status_code=404, detail="Project not active. Call GET /projects first.")
    return store.active_project.base_path


@router.post("/reset", response_model=TaskMutationResponse)
async def reset_task_to_todo(project_id: str, request: TaskResetRequest):
    roadmap_dir = _get_project_roadmap_dir(project_id)
    roadmap_id = request.roadmap_id or "roadmap.json"
    variants = _discover_roadmap_variants(roadmap_dir)
    roadmap_entry = variants.get(roadmap_id)
    if not roadmap_entry:
        raise HTTPException(status_code=404, detail="Requested roadmap not found.")
    if roadmap_entry.get("payload") is None:
        raise HTTPException(status_code=409, detail=roadmap_entry.get("load_warning") or "Requested roadmap could not be loaded.")
    roadmap = roadmap_entry["payload"]

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
    async with RunCoordinator.event_write(project_id):
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
    variants = _discover_roadmap_variants(roadmap_dir)
    roadmap_entry = variants.get(roadmap_id)
    if not roadmap_entry:
        raise HTTPException(status_code=404, detail="Requested roadmap not found.")
    if roadmap_entry.get("payload") is None:
        raise HTTPException(status_code=409, detail=roadmap_entry.get("load_warning") or "Requested roadmap could not be loaded.")
    roadmap = roadmap_entry["payload"]

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

    async with RunCoordinator.event_write(project_id):
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


@router.patch("/{task_id}/planning", response_model=TaskPlanningMutationResponse)
async def update_task_planning(project_id: str, task_id: str, request: TaskPlanningUpdateRequest):
    roadmap_dir = _get_project_roadmap_dir(project_id)
    roadmap_id = request.roadmap_id or "roadmap.json"
    variants = _discover_roadmap_variants(roadmap_dir)
    roadmap_entry = variants.get(roadmap_id)
    if not roadmap_entry:
        raise HTTPException(status_code=404, detail="Requested roadmap not found.")
    if roadmap_entry.get("payload") is None:
        raise HTTPException(status_code=409, detail=roadmap_entry.get("load_warning") or "Requested roadmap could not be loaded.")
    roadmap = roadmap_entry["payload"]

    task = next((item for item in roadmap.get("tasks", []) if item.get("task_id") == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    preferred_runner = request.preferred_runner
    if preferred_runner is None:
        current_planning = task.get("planning", {}) if isinstance(task.get("planning"), dict) else {}
        preferred_runner = current_planning.get("preferred_runner")
    if not preferred_runner:
        raise HTTPException(status_code=422, detail="preferred_runner is required to persist task planning.")
    try:
        AgentRouter().get_adapter(preferred_runner)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail="Unknown preferred_runner.") from exc

    planning = {
        "preferred_runner": preferred_runner,
    }

    async with RunCoordinator.event_write(project_id):
        writer = EventWriter(roadmap_dir=roadmap_dir)
        event = writer.append_event(
            actor="orchestrator",
            action="orchestrator.view.mutate",
            payload={
                "task_id": task_id,
                "planning": planning,
            },
        )
        Projector(roadmap_dir, roadmap_id=roadmap_id).sync_to_disk([event])

    return TaskPlanningMutationResponse(
        task_id=task_id,
        roadmap_id=roadmap_id,
        planning=planning,
        message="Task planning updated.",
    )
