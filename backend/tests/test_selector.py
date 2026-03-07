from app.core.selector import TaskSelector


def _roadmap(tasks: list) -> dict:
    return {"tasks": tasks, "indexes": {"by_status": {}}}


def _task(task_id: str, status: str, depends_on: list = None) -> dict:
    return {
        "task_id": task_id,
        "task_kind": "impl",
        "title": task_id,
        "description": "",
        "status": status,
        "depends_on": depends_on or [],
        "targets": [],
        "outputs": {"files": []},
        "immutability": {"done_is_immutable": True},
        "required_verification": [],
    }


def test_selects_first_eligible_todo_task() -> None:
    roadmap = _roadmap([
        _task("T-001", "done"),
        _task("T-002", "todo"),
        _task("T-003", "todo"),
    ])
    selector = TaskSelector(roadmap)
    result = selector.select_next_task()
    assert result is not None
    assert result["task_id"] == "T-002"


def test_returns_none_when_no_eligible_task() -> None:
    roadmap = _roadmap([
        _task("T-001", "done"),
        _task("T-002", "in_progress"),
    ])
    selector = TaskSelector(roadmap)
    assert selector.select_next_task() is None


def test_respects_unresolved_dependencies() -> None:
    roadmap = _roadmap([
        _task("T-001", "todo"),
        _task("T-002", "todo", depends_on=["T-001"]),
    ])
    selector = TaskSelector(roadmap)
    result = selector.select_next_task()
    assert result["task_id"] == "T-001"


def test_eligible_after_dependency_done() -> None:
    roadmap = _roadmap([
        _task("T-001", "done"),
        _task("T-002", "todo", depends_on=["T-001"]),
    ])
    selector = TaskSelector(roadmap)
    result = selector.select_next_task()
    assert result["task_id"] == "T-002"


def test_get_eligible_tasks_returns_all_eligible() -> None:
    roadmap = _roadmap([
        _task("T-001", "todo"),
        _task("T-002", "todo"),
        _task("T-003", "done"),
        _task("T-004", "todo", depends_on=["T-003"]),
    ])
    selector = TaskSelector(roadmap)
    eligible = selector.get_eligible_tasks()
    ids = {t["task_id"] for t in eligible}
    assert ids == {"T-001", "T-002", "T-004"}


def test_status_report_includes_ineligibility_reasons() -> None:
    roadmap = _roadmap([
        _task("T-001", "in_progress"),
        _task("T-002", "todo", depends_on=["T-001"]),
    ])
    selector = TaskSelector(roadmap)
    report = {r["task_id"]: r for r in selector.get_task_status_report()}

    assert report["T-001"]["is_eligible"] is False
    assert report["T-002"]["is_eligible"] is False
    assert any("T-001" in reason for reason in report["T-002"]["reasons"])


def test_open_critical_issue_does_not_block_non_target_tasks() -> None:
    roadmap = _roadmap([_task("T-001", "todo")])
    open_issues = [{"issue_id": "ISS-001", "status": "open", "severity": "medium", "title": "gap"}]
    selector = TaskSelector(roadmap, open_issues)
    result = selector.select_next_task()
    assert result["task_id"] == "T-001"
