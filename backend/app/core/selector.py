from typing import List, Dict, Any, Optional
from app.core.eligibility import EligibilityEngine

class TaskSelector:
    def __init__(self, roadmap: Dict[str, Any], open_issues: List[Dict[str, Any]] = None):
        self.roadmap = roadmap
        self.engine = EligibilityEngine(roadmap, open_issues)

    def select_next_task(self) -> Optional[Dict[str, Any]]:
        tasks = self.roadmap.get("tasks", [])
        for task in tasks:
            is_eligible, _ = self.engine.check_eligibility(task["task_id"])
            if is_eligible:
                return task
        return None

    def get_eligible_tasks(self) -> List[Dict[str, Any]]:
        eligible = []
        tasks = self.roadmap.get("tasks", [])
        for task in tasks:
            is_eligible, reasons = self.engine.check_eligibility(task["task_id"])
            if is_eligible:
                eligible.append(task)
        return eligible

    def get_task_status_report(self) -> List[Dict[str, Any]]:
        report = []
        tasks = self.roadmap.get("tasks", [])
        for task in tasks:
            is_eligible, reasons = self.engine.check_eligibility(task["task_id"])
            report.append({
                "task_id": task["task_id"],
                "status": task["status"],
                "is_eligible": is_eligible,
                "reasons": reasons
            })
        return report
