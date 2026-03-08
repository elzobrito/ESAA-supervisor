from fastapi import APIRouter, HTTPException
from app.api.schemas import RunResponse, RunStartRequest, RunTaskRequest, RunDecisionRequest, RunCancelResponse, RunStopResponse, EligibilityReportResponse, EligibilityEntry
from app.core.selector import TaskSelector
from app.core.run_engine import RunEngine
from app.core.eligibility import EligibilityEngine
from app.api.routes_projects import store
from app.api.routes_state import _discover_roadmap_variants, _load_roadmap_variants

router = APIRouter(prefix="/projects/{project_id}/runs", tags=["runs"])


def _get_active_store(project_id: str):
    if not store.active_project or store.active_project.id != project_id:
        raise HTTPException(status_code=404, detail="Project not found. Call GET /projects first.")
    return store


def _build_open_issues(raw_issues) -> list:
    if isinstance(raw_issues, dict):
        issues_list = raw_issues.get("issues", [])
    else:
        issues_list = raw_issues or []
    return [i for i in issues_list if i.get("status") == "open"]


def _extract_lessons(raw_lessons) -> list:
    if isinstance(raw_lessons, dict):
        return raw_lessons.get("lessons", [])
    return raw_lessons or []


def _to_run_response(run_state) -> RunResponse:
    return RunResponse(
        run_id=run_state.run_id,
        task_id=run_state.task_id,
        agent_id=run_state.agent_id,
        model_id=run_state.model_id,
        reasoning_effort=run_state.reasoning_effort,
        roadmap_id=run_state.roadmap_id,
        execution_mode=run_state.execution_mode,
        status=run_state.status,
        started_at=run_state.started_at,
        ended_at=run_state.ended_at,
        exit_code=run_state.exit_code,
        error_message=run_state.error_message,
        awaiting_decision=run_state.awaiting_decision,
        proposed_action=run_state.proposed_action,
        available_actions=run_state.available_actions,
        agent_result=run_state.agent_result,
        decision_history=[entry.model_dump(mode="json") for entry in run_state.decision_history],
        logs=[entry.model_dump(mode="json") for entry in run_state.logs],
        completed_task_ids=run_state.completed_task_ids,
        stop_after_current=run_state.stop_after_current,
    )


def _resolve_roadmap(project_id: str, roadmap_id: str | None) -> dict:
    if not store.active_project or store.active_project.id != project_id:
        raise HTTPException(status_code=404, detail="Project not found. Call GET /projects first.")
    roadmap_key = roadmap_id or "roadmap.json"
    if roadmap_key == "aggregate":
        raise HTTPException(status_code=422, detail="Runs require a specific roadmap, not aggregate mode.")
    variants = _discover_roadmap_variants(store.active_project.base_path)
    selected = variants.get(roadmap_key)
    if not selected:
        raise HTTPException(status_code=404, detail="Requested roadmap not found for execution.")
    if selected.get("payload") is None:
        raise HTTPException(status_code=409, detail=selected.get("load_warning") or "Requested roadmap could not be loaded for execution.")
    return selected["payload"]


@router.get("/eligibility", response_model=EligibilityReportResponse)
async def get_eligibility_report(project_id: str):
    s = _get_active_store(project_id)
    raw = s.get_state()
    open_issues = _build_open_issues(raw.issues)
    engine = EligibilityEngine(raw.roadmap, open_issues)
    selector = TaskSelector(raw.roadmap, open_issues)
    report = selector.get_task_status_report()
    eligible_count = sum(1 for r in report if r["is_eligible"])
    return EligibilityReportResponse(
        eligible_count=eligible_count,
        tasks=[
            EligibilityEntry(
                task_id=r["task_id"],
                status=r["status"],
                is_eligible=r["is_eligible"],
                reasons=r.get("reasons", []),
            )
            for r in report
        ],
    )


@router.post("/next", response_model=RunResponse)
async def start_next_run(project_id: str, request: RunStartRequest):
    s = _get_active_store(project_id)
    raw = s.get_state()
    open_issues = _build_open_issues(raw.issues)
    lessons = _extract_lessons(raw.lessons)
    roadmap = _resolve_roadmap(project_id, request.roadmap_id)
    selector = TaskSelector(roadmap, open_issues)
    next_task = selector.select_next_task()

    if not next_task:
        raise HTTPException(status_code=422, detail="No eligible tasks found")

    engine = RunEngine(project_id)
    try:
        run_state = await engine.start_run(
            next_task["task_id"],
            request.agent_id,
            request.roadmap_id,
            request.execution_mode,
            roadmap_dir=s.active_project.base_path,
            roadmap=roadmap,
            lessons=lessons,
            allow_in_progress=False,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))

    return _to_run_response(run_state)


@router.post("/task", response_model=RunResponse)
async def start_task_run(project_id: str, request: RunTaskRequest):
    s = _get_active_store(project_id)
    raw = s.get_state()
    open_issues = _build_open_issues(raw.issues)
    lessons = _extract_lessons(raw.lessons)
    roadmap = _resolve_roadmap(project_id, request.roadmap_id)

    # Validate the requested task is eligible
    engine_el = EligibilityEngine(roadmap, open_issues)
    is_eligible, reasons = engine_el.check_runnable(request.task_id, allow_in_progress=True)
    if not is_eligible:
        raise HTTPException(
            status_code=422,
            detail={"message": "Task is not runnable", "reasons": reasons},
        )

    engine = RunEngine(project_id)
    try:
        run_state = await engine.start_run(
            request.task_id,
            request.agent_id,
            request.roadmap_id,
            request.execution_mode,
            roadmap_dir=s.active_project.base_path,
            roadmap=roadmap,
            lessons=lessons,
            allow_in_progress=True,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=409, detail=str(e))

    return _to_run_response(run_state)


@router.post("/{run_id}/decision", response_model=RunResponse)
async def submit_run_decision(project_id: str, run_id: str, request: RunDecisionRequest):
    run_state = RunEngine.get_run_state(run_id)
    if not run_state:
        raise HTTPException(status_code=404, detail="Run not found")
    if not run_state.awaiting_decision:
        raise HTTPException(status_code=409, detail="Run is not waiting for manual decision")
    if request.decision not in {"apply", "reject"}:
        raise HTTPException(status_code=422, detail="Decision must be 'apply' or 'reject'")
    if request.selected_action and request.selected_action not in {"claim", "complete", "issue.report"}:
        raise HTTPException(status_code=422, detail="Unsupported selected action")

    updated = RunEngine.submit_decision(run_id, request.decision, request.selected_action)
    if not updated:
        raise HTTPException(status_code=404, detail="Run not found")
    return _to_run_response(updated)


@router.delete("/{run_id}", response_model=RunCancelResponse)
async def cancel_run(project_id: str, run_id: str):
    run_state = RunEngine.get_run_state(run_id)
    if not run_state:
        raise HTTPException(status_code=404, detail="Run not found")

    from app.models.run_state import RunStatus
    if run_state.status in (RunStatus.DONE, RunStatus.ERROR, RunStatus.CANCELLED):
        return RunCancelResponse(
            run_id=run_id,
            cancelled=False,
            message=f"Run already finished with status {run_state.status}",
        )

    cancelled = RunEngine.cancel_run(project_id, run_id)

    return RunCancelResponse(
        run_id=run_id,
        cancelled=cancelled,
        message="Cancellation requested" if cancelled else "Run could not be cancelled",
    )


@router.post("/{run_id}/stop-after-current", response_model=RunStopResponse)
async def stop_after_current(project_id: str, run_id: str):
    run_state = RunEngine.get_run_state(run_id)
    if not run_state:
        raise HTTPException(status_code=404, detail="Run not found")

    from app.models.run_state import RunExecutionMode, RunStatus
    if run_state.execution_mode != RunExecutionMode.CONTINUOUS:
        raise HTTPException(status_code=409, detail="Graceful stop is only available for continuous runs")
    if run_state.status in (RunStatus.DONE, RunStatus.ERROR, RunStatus.CANCELLED):
        raise HTTPException(status_code=409, detail=f"Run already finished with status {run_state.status}")

    updated = RunEngine.request_stop_after_current(run_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunStopResponse(
        run_id=run_id,
        stop_after_current=updated.stop_after_current,
        message="Run will stop after the current task finishes",
    )


@router.get("/{run_id}")
async def get_run_status(project_id: str, run_id: str):
    run_state = RunEngine.get_run_state(run_id)
    if not run_state:
        raise HTTPException(status_code=404, detail="Run not found")
    return _to_run_response(run_state)


@router.get("", response_model=list[RunResponse])
async def list_runs(project_id: str):
    _get_active_store(project_id)
    return [_to_run_response(run_state) for run_state in RunEngine.list_runs(project_id)]
