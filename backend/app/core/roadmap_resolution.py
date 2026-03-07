import os
from typing import List, Optional
from app.models.canonical_artifact import CanonicalArtifact, ArtifactRole

class RoadmapResolution:
    def __init__(self, artifacts: List[CanonicalArtifact]):
        self.artifacts = artifacts

    def resolve_active_roadmap(self) -> Optional[str]:
        # Priority 1: roadmap.json (canonical)
        for art in self.artifacts:
            if art.role == ArtifactRole.ROADMAP and art.file_name == "roadmap.json":
                return art.file_path
        
        # Priority 2: Any roadmap.*.json (plugins)
        for art in self.artifacts:
            if art.role == ArtifactRole.ROADMAP and art.file_name.startswith("roadmap."):
                return art.file_path
                
        return None

    def get_all_roadmaps(self) -> List[str]:
        return [art.file_path for art in self.artifacts if art.role == ArtifactRole.ROADMAP]
