from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.run_state import RunStatus


class ProjectResponse(BaseModel):
    id: str
    name: str
    base_path: str
    project_path: Optional[str] = None
    is_active: bool


class FileSystemEntryResponse(BaseModel):
    name: str
    path: str


class ProjectFileEntryResponse(BaseModel):
    name: str
    path: str
    kind: str


class ProjectBrowserResponse(BaseModel):
    current_path: str
    parent_path: Optional[str] = None
    directories: List[FileSystemEntryResponse] = []
    projects: List[ProjectResponse] = []


class OpenProjectRequest(BaseModel):
    path: str


class ArtifactContentResponse(BaseModel):
    path: str
    content: str
    truncated: bool = False
    encoding: str = "utf-8"
    size_bytes: int


class ProjectFileBrowserResponse(BaseModel):
    current_path: str
    parent_path: Optional[str] = None
    directories: List[ProjectFileEntryResponse] = []
    files: List[ProjectFileEntryResponse] = []


class RoadmapOptionResponse(BaseModel):
    roadmap_id: str
    label: str
    task_count: int
    is_default: bool = False
    is_consistent: bool = False


class ArtifactResponse(BaseModel):
    name: str
    path: str
    category: str
    role: str
    integrity_status: str


class ActivityEventResponse(BaseModel):
    event_seq: int
    event_id: str
    ts: str
    actor: str
    action: str
    task_id: Optional[str] = None
    prior_status: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class TaskResponse(BaseModel):
    task_ref: str
    task_id: str
    roadmap_id: str
    roadmap_label: str
    task_kind: str
    title: str
    description: str
    status: str
    assigned_to: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    depends_on: List[str] = []
    is_eligible: bool = False
    ineligibility_reasons: List[str] = []


class IssueResponse(BaseModel):
    issue_id: str
    status: str
    severity: str
    title: str


class LessonResponse(BaseModel):
    lesson_id: str
    status: str
    title: str
    rule: str


class AgentOptionResponse(BaseModel):
    agent_id: str
    label: str
    available: bool
    command: str


class StateResponse(BaseModel):
    project: ProjectResponse
    last_event_seq: int
    is_consistent: bool
    roadmap_mode: str = "single"
    selected_roadmap_id: str = "roadmap.json"
    available_roadmaps: List[RoadmapOptionResponse] = []
    available_agents: List[AgentOptionResponse] = []
    tasks: List[TaskResponse] = []
    open_issues: List[IssueResponse] = []
    lessons: List[LessonResponse] = []
    artifacts: List[ArtifactResponse] = []
    activity: List[ActivityEventResponse] = []
    eligible_task_ids: List[str] = []


class RunStartRequest(BaseModel):
    agent_id: Optional[str] = "gemini-cli"
    roadmap_id: Optional[str] = "roadmap.json"


class RunTaskRequest(BaseModel):
    task_id: str
    agent_id: Optional[str] = "gemini-cli"
    roadmap_id: Optional[str] = "roadmap.json"


class RunDecisionRequest(BaseModel):
    decision: str
    selected_action: Optional[str] = None


class TaskResetRequest(BaseModel):
    task_id: str
    roadmap_id: Optional[str] = "roadmap.json"


class TaskMutationResponse(BaseModel):
    task_id: str
    roadmap_id: str
    status: str
    message: str


class IssueResolveRequest(BaseModel):
    issue_id: str
    resolution_summary: Optional[str] = None


class IssueMutationResponse(BaseModel):
    issue_id: str
    status: str
    message: str


class IntegrityRepairRequest(BaseModel):
    roadmap_id: Optional[str] = None


class IntegrityRepairResponse(BaseModel):
    repaired_roadmaps: List[str] = []
    artifact_issues_after: int
    is_consistent: bool
    message: str


class RunLogResponse(BaseModel):
    timestamp: datetime
    source: str
    content: str


class RunDecisionEntryResponse(BaseModel):
    timestamp: datetime
    stage: str
    proposed_action: Optional[str] = None
    selected_action: Optional[str] = None
    decision: Optional[str] = None
    actor: Optional[str] = None
    notes: Optional[str] = None


class RunResponse(BaseModel):
    run_id: str
    task_id: str
    agent_id: str
    roadmap_id: Optional[str] = None
    status: RunStatus
    started_at: datetime
    ended_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    awaiting_decision: bool = False
    proposed_action: Optional[str] = None
    available_actions: List[str] = []
    agent_result: Optional[Dict[str, Any]] = None
    decision_history: List[RunDecisionEntryResponse] = []
    logs: List[RunLogResponse] = []


class RunCancelResponse(BaseModel):
    run_id: str
    cancelled: bool
    message: str


class EligibilityEntry(BaseModel):
    task_id: str
    status: str
    is_eligible: bool
    reasons: List[str] = []


class EligibilityReportResponse(BaseModel):
    eligible_count: int
    tasks: List[EligibilityEntry] = []
