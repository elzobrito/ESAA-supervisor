import os
from typing import Optional

from app.core.artifact_discovery import ArtifactDiscovery
from app.core.projector import Projector
from app.core.validators import ArtifactValidator
from app.models.project_state import ConsolidatedState, ProjectMetadata
from app.utils.json_artifacts import JsonArtifactLoadError, load_json_artifact
from app.utils.jsonl import read_jsonl

class CanonicalStore:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.active_project: Optional[ProjectMetadata] = None
        self.discovered_artifacts = []

    def load_project(self, project_id: str, roadmap_path: str):
        self.active_project = ProjectMetadata(
            id=project_id,
            name=os.path.basename(os.path.dirname(roadmap_path)),
            base_path=roadmap_path,
            is_active=True
        )
        discovery = ArtifactDiscovery(roadmap_path)
        validator = ArtifactValidator(roadmap_path)
        self.discovered_artifacts = []
        for artifact in discovery.discover():
            validation = validator.validate(artifact)
            integrity_status = "ok" if validation["is_valid"] else "error"
            self.discovered_artifacts.append(artifact.model_copy(update={"integrity_status": integrity_status}))

    def get_state(self) -> ConsolidatedState:
        if not self.active_project:
            raise ValueError("No active project loaded")

        state = ConsolidatedState(
            project=self.active_project,
            artifacts=self.discovered_artifacts
        )

        # Basic loading of projection files if they exist
        roadmap_file = os.path.join(self.active_project.base_path, "roadmap.json")
        if os.path.exists(roadmap_file):
            try:
                state.roadmap = load_json_artifact(roadmap_file).payload
                state.last_event_seq = state.roadmap.get("meta", {}).get("run", {}).get("last_event_seq", 0)
                state.is_consistent = self._is_consistent(state.roadmap)
            except JsonArtifactLoadError:
                state.roadmap = {}
                state.last_event_seq = 0
                state.is_consistent = False

        issues_file = os.path.join(self.active_project.base_path, "issues.json")
        if os.path.exists(issues_file):
            try:
                state.issues = load_json_artifact(issues_file).payload
            except JsonArtifactLoadError:
                state.issues = {"issues": []}

        lessons_file = os.path.join(self.active_project.base_path, "lessons.json")
        if os.path.exists(lessons_file):
            try:
                state.lessons = load_json_artifact(lessons_file).payload
            except JsonArtifactLoadError:
                state.lessons = {"lessons": []}

        activity_file = os.path.join(self.active_project.base_path, "activity.jsonl")
        if os.path.exists(activity_file):
            state.activity = read_jsonl(activity_file)[-25:]

        return state

    def _is_consistent(self, roadmap: dict) -> bool:
        verify_status = roadmap.get("meta", {}).get("run", {}).get("verify_status")
        stored_hash = roadmap.get("meta", {}).get("run", {}).get("projection_hash_sha256")
        if verify_status != "ok" or not stored_hash:
            return False

        try:
            computed_hash = Projector.compute_projection_hash(roadmap)
        except Exception:
            return False
        return computed_hash == stored_hash
