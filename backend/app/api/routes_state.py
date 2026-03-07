import json
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.api.routes_projects import store
from app.api.schemas import (
    ActivityEventResponse,
    ActiveRunResponse,
    AgentOptionResponse,
    AgentModelOptionResponse,
    AgentReasoningOptionResponse,
    ArtifactResponse,
    IssueResponse,
    LessonResponse,
    ProjectResponse,
    RoadmapOptionResponse,
    StateResponse,
    TaskResponse,
)
from app.core.agent_model_catalog import AgentModelCatalog
from app.core.agent_router import AgentRouter
from app.core.run_coordinator import RunCoordinator
from app.core.run_engine import RunEngine
from app.core.selector import TaskSelector

router = APIRouter(prefix="/projects/{project_id}/state", tags=["state"])


def _load_roadmap_variants(base_path: str) -> Dict[str, Dict[str, Any]]:
    variants: Dict[str, Dict[str, Any]] = {}
    for entry in sorted(os.scandir(base_path), key=lambda item: item.name.lower()):
        if not entry.is_file():
            continue
        if not entry.name.startswith("roadmap") or not entry.name.endswith(".json"):
            continue
        with open(entry.path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload.get("tasks"), list):
            continue
        variants[entry.name] = payload
    return variants


def _roadmap_label(roadmap_id: str) -> str:
    if roadmap_id == "roadmap.json":
        return "Principal"
    if roadmap_id.startswith("roadmap.") and roadmap_id.endswith(".json"):
        return roadmap_id[len("roadmap."):-len(".json")]
    return roadmap_id


def _agent_label(agent_id: str) -> str:
    labels = {
        "codex": "Codex",
        "claude-code": "Claude Code",
        "gemini-cli": "Gemini CLI",
    }
    return labels.get(agent_id, agent_id)


def _build_task_rows(
    project_id: str,
    roadmap_id: str,
    roadmap_label: str,
    roadmap: Dict[str, Any],
    open_issues: List[Dict[str, Any]],
) -> tuple[List[TaskResponse], List[str]]:
    selector = TaskSelector(roadmap, open_issues)
    status_report = {row["task_id"]: row for row in selector.get_task_status_report()}
    active_runs = {run.task_id: run for run in RunEngine.list_runs(project_id) if run.roadmap_id == roadmap_id}
    tasks: List[TaskResponse] = []
    eligible_ids: List[str] = []

    for task in roadmap.get("tasks", []):
        task_id = task["task_id"]
        task_ref = f"{roadmap_id}:{task_id}"
        report = status_report.get(task_id, {})
        is_eligible = report.get("is_eligible", False)
        active_run = active_runs.get(task_id)
        planning = task.get("planning", {}) if isinstance(task.get("planning"), dict) else {}
        preferred_runner = planning.get("preferred_runner")
        if not preferred_runner:
            preferred_runner = AgentRouter.default_runner_for_kind(task.get("task_kind", ""))
        if is_eligible:
            eligible_ids.append(task_ref)
        tasks.append(TaskResponse(
            task_ref=task_ref,
            task_id=task_id,
            roadmap_id=roadmap_id,
            roadmap_label=roadmap_label,
            task_kind=task.get("task_kind", ""),
            title=task.get("title", ""),
            description=task.get("description", ""),
            status=task.get("status", ""),
            assigned_to=task.get("assigned_to"),
            active_run_id=active_run.run_id if active_run else None,
            active_agent=active_run.agent_id if active_run else None,
            active_model=active_run.model_id if active_run else None,
            started_at=task.get("started_at"),
            completed_at=task.get("completed_at"),
            depends_on=task.get("depends_on", []),
            is_eligible=is_eligible,
            ineligibility_reasons=report.get("reasons", []),
            planning={
                "preferred_runner": preferred_runner,
            },
        ))

    return tasks, eligible_ids


@router.get("", response_model=StateResponse)
async def get_project_state(project_id: str, roadmap: Optional[str] = Query(default=None)):
    if not store.active_project or store.active_project.id != project_id:
        raise HTTPException(status_code=404, detail="Project not active. Call GET /projects first.")

    store.load_project(project_id, store.active_project.base_path)
    raw = store.get_state()

    roadmap_variants = _load_roadmap_variants(store.active_project.base_path)
    if not roadmap_variants:
        raise HTTPException(status_code=404, detail="No roadmap files found for project.")

    selected_roadmap_id = roadmap or ("roadmap.json" if "roadmap.json" in roadmap_variants else next(iter(roadmap_variants)))
    aggregate_mode = selected_roadmap_id == "aggregate"
    if not aggregate_mode and selected_roadmap_id not in roadmap_variants:
        raise HTTPException(status_code=404, detail="Requested roadmap not found.")

    issues_data = raw.issues
    lessons_data = raw.lessons

    if isinstance(issues_data, dict):
        issues_list = issues_data.get("issues", [])
    else:
        issues_list = issues_data or []

    if isinstance(lessons_data, dict):
        lessons_list = lessons_data.get("lessons", [])
    else:
        lessons_list = lessons_data or []

    open_issues = [issue for issue in issues_list if issue.get("status") == "open"]
    active_runs = RunEngine.list_runs(project_id)
    busy_agents = RunCoordinator.busy_agents(project_id)

    available_roadmaps = [
        RoadmapOptionResponse(
            roadmap_id=roadmap_id,
            label=_roadmap_label(roadmap_id),
            task_count=len(candidate.get("tasks", [])),
            is_default=roadmap_id == "roadmap.json",
            is_consistent=store._is_consistent(candidate),
        )
        for roadmap_id, candidate in roadmap_variants.items()
    ]
    router = AgentRouter()
    available_agents = [
        AgentOptionResponse(
            agent_id=agent_id,
            label=_agent_label(agent_id),
            available=adapter.is_available(),
            command=adapter.resolve_command(),
            busy=agent_id in busy_agents,
            default_model=catalog_entry.default_model,
            models=[
                AgentModelOptionResponse(
                    model_id=model.model_id,
                    label=model.label,
                    is_default=model.model_id == catalog_entry.default_model,
                )
                for model in catalog_entry.models
            ],
            default_reasoning_effort=catalog_entry.default_reasoning_effort,
            reasoning_efforts=[
                AgentReasoningOptionResponse(
                    effort_id=effort.effort_id,
                    label=effort.label,
                    is_default=effort.effort_id == catalog_entry.default_reasoning_effort,
                )
                for effort in catalog_entry.reasoning_efforts
            ],
        )
        for agent_id, adapter in router.adapters.items()
        for catalog_entry in [AgentModelCatalog.get_entry(agent_id, roadmap_dir=store.active_project.base_path)]
    ]

    tasks: List[TaskResponse] = []
    eligible_ids: List[str] = []
    if aggregate_mode:
        for roadmap_id, candidate in roadmap_variants.items():
            rows, eligible = _build_task_rows(project_id, roadmap_id, _roadmap_label(roadmap_id), candidate, open_issues)
            tasks.extend(rows)
            eligible_ids.extend(eligible)
        last_event_seq = max(candidate.get("meta", {}).get("run", {}).get("last_event_seq", 0) for candidate in roadmap_variants.values())
        is_consistent = all(store._is_consistent(candidate) for candidate in roadmap_variants.values())
    else:
        selected = roadmap_variants[selected_roadmap_id]
        tasks, eligible_ids = _build_task_rows(project_id, selected_roadmap_id, _roadmap_label(selected_roadmap_id), selected, open_issues)
        last_event_seq = selected.get("meta", {}).get("run", {}).get("last_event_seq", 0)
        is_consistent = store._is_consistent(selected)

    open_issue_responses = [
        IssueResponse(
            issue_id=issue["issue_id"],
            status=issue["status"],
            severity=issue.get("severity", ""),
            title=issue["title"],
        )
        for issue in issues_list
        if issue.get("status") == "open"
    ]

    lesson_responses = [
        LessonResponse(
            lesson_id=lesson["lesson_id"],
            status=lesson.get("status", "active"),
            title=lesson["title"],
            rule=lesson.get("rule", ""),
        )
        for lesson in lessons_list
    ]

    artifact_responses = [
        ArtifactResponse(
            name=artifact.file_name,
            path=artifact.file_path,
            category=artifact.category.value,
            role=artifact.role.value,
            integrity_status=artifact.integrity_status,
        )
        for artifact in raw.artifacts
    ]

    activity_responses = [
        ActivityEventResponse(
            event_seq=event.get("event_seq", 0),
            event_id=event.get("event_id", ""),
            ts=event.get("ts", ""),
            actor=event.get("actor", ""),
            action=event.get("action", ""),
            task_id=event.get("task_id") or event.get("payload", {}).get("task_id"),
            prior_status=event.get("prior_status") or event.get("payload", {}).get("prior_status"),
            payload=event.get("payload", {}),
        )
        for event in raw.activity
    ]

    return StateResponse(
        project=ProjectResponse(
            id=raw.project.id,
            name=raw.project.name,
            base_path=raw.project.base_path,
            is_active=raw.project.is_active,
        ),
        last_event_seq=last_event_seq,
        is_consistent=is_consistent,
        roadmap_mode="aggregate" if aggregate_mode else "single",
        selected_roadmap_id=selected_roadmap_id,
        available_roadmaps=available_roadmaps,
        available_agents=available_agents,
        active_runs=[
            ActiveRunResponse(
                run_id=run.run_id,
                task_id=run.task_id,
                agent_id=run.agent_id,
                model_id=run.model_id,
                reasoning_effort=run.reasoning_effort,
                roadmap_id=run.roadmap_id,
                execution_mode=run.execution_mode,
                status=run.status,
                started_at=run.started_at,
                awaiting_decision=run.awaiting_decision,
            )
            for run in active_runs
        ],
        active_run_count=len(active_runs),
        remaining_run_slots=RunCoordinator.remaining_slots(project_id),
        busy_agents=busy_agents,
        tasks=tasks,
        open_issues=open_issue_responses,
        lessons=lesson_responses,
        artifacts=artifact_responses,
        activity=activity_responses,
        eligible_task_ids=eligible_ids,
    )
