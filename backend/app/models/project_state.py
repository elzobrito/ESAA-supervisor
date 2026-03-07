from typing import Any, Dict, List

from pydantic import BaseModel, Field

from app.models.canonical_artifact import CanonicalArtifact


class ProjectMetadata(BaseModel):
    id: str
    name: str
    base_path: str
    is_active: bool = False


class ConsolidatedState(BaseModel):
    project: ProjectMetadata
    artifacts: List[CanonicalArtifact] = Field(default_factory=list)
    roadmap: Dict[str, Any] = Field(default_factory=dict)
    issues: Dict[str, Any] = Field(default_factory=dict)
    lessons: Dict[str, Any] = Field(default_factory=dict)
    activity: List[Dict[str, Any]] = Field(default_factory=list)
    last_event_seq: int = 0
    is_consistent: bool = True
