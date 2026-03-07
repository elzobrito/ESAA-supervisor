from enum import Enum
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

class RunStatus(str, Enum):
    PREFLIGHT = "preflight"
    RUNNING = "running"
    WAITING_INPUT = "waiting_input"
    SYNCING = "syncing"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    DONE = "done"
    ERROR = "error"

class RunLogEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str  # stdout, stderr, system
    content: str


class RunDecisionEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    stage: str
    proposed_action: Optional[str] = None
    selected_action: Optional[str] = None
    decision: Optional[str] = None
    actor: Optional[str] = None
    notes: Optional[str] = None


class RunState(BaseModel):
    run_id: str
    task_id: str
    agent_id: str
    roadmap_id: Optional[str] = None
    status: RunStatus = RunStatus.PREFLIGHT
    started_at: datetime = Field(default_factory=datetime.now)
    ended_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    error_message: Optional[str] = None
    awaiting_decision: bool = False
    proposed_action: Optional[str] = None
    available_actions: List[str] = Field(default_factory=list)
    agent_result: Optional[Dict[str, Any]] = None
    decision_history: List[RunDecisionEntry] = Field(default_factory=list)
    logs: List[RunLogEntry] = Field(default_factory=list)
