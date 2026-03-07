from typing import List, Dict, Any, Tuple

class EligibilityEngine:
    def __init__(self, roadmap: Dict[str, Any], open_issues: List[Dict[str, Any]] = None):
        self.roadmap = roadmap
        self.open_issues = open_issues or []
        self.tasks = {t["task_id"]: t for t in roadmap.get("tasks", [])}

    def check_eligibility(self, task_id: str) -> Tuple[bool, List[str]]:
        return self.check_runnable(task_id)

    def check_runnable(self, task_id: str, *, allow_in_progress: bool = False) -> Tuple[bool, List[str]]:
        task = self.tasks.get(task_id)
        if not task:
            return False, ["Task not found"]

        reasons = []
        
        # 1. Status must be runnable
        allowed_statuses = {"todo", "in_progress"} if allow_in_progress else {"todo"}
        if task["status"] not in allowed_statuses:
            expected = "todo or in_progress" if allow_in_progress else "todo"
            reasons.append(f"Task status is {task['status']}, expected {expected}")

        # 2. Dependencies must be "done"
        for dep_id in task.get("depends_on", []):
            dep_task = self.tasks.get(dep_id)
            if not dep_task:
                reasons.append(f"Dependency {dep_id} not found")
            elif dep_task["status"] != "done":
                reasons.append(f"Dependency {dep_id} is {dep_task['status']}")

        # 3. Check for blocking issues
        for issue in self.open_issues:
            # If issue blocks this specific task
            if issue.get("blocked_task_id") == task_id and issue.get("status") == "open":
                reasons.append(f"Blocked by issue {issue.get('issue_id')}: {issue.get('title')}")
            # If it's a critical project-wide issue
            elif issue.get("severity") == "critical" and issue.get("status") == "open":
                reasons.append(f"Blocked by critical project issue {issue.get('issue_id')}")

        is_eligible = len(reasons) == 0
        return is_eligible, reasons
