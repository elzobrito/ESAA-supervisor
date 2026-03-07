from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ArtifactCategory(str, Enum):
    SOURCE_OF_TRUTH = "source_of_truth"
    PROJECTION = "projection"
    CONTRACT = "contract"
    POLICY = "policy"
    SCHEMA = "schema"
    PROFILE = "profile"
    SNAPSHOT = "snapshot"
    SWARM = "swarm"

class ArtifactRole(str, Enum):
    ACTIVITY = "activity"
    ROADMAP = "roadmap"
    ISSUES = "issues"
    LESSONS = "lessons"
    ORCHESTRATOR_CONTRACT = "orchestrator_contract"
    AGENT_CONTRACT = "agent_contract"
    RUNTIME_POLICY = "runtime_policy"
    STORAGE_POLICY = "storage_policy"
    PARCER_PROFILE = "parcer_profile"
    JSON_SCHEMA = "json_schema"
    SWARM_CONFIG = "swarm_config"
    GENERIC = "generic"

class CanonicalArtifact(BaseModel):
    file_path: str
    file_name: str
    category: ArtifactCategory
    role: ArtifactRole
    plugin_id: Optional[str] = None
    integrity_status: str = "unknown"  # unknown, ok, error, mismatch
    last_modified: str
    size_bytes: int
    version: Optional[str] = None
