import os
import datetime
from typing import List, Optional
from app.models.canonical_artifact import CanonicalArtifact, ArtifactCategory, ArtifactRole

class ArtifactDiscovery:
    def __init__(self, roadmap_dir: str):
        self.roadmap_dir = roadmap_dir

    def discover(self) -> List[CanonicalArtifact]:
        artifacts = []
        if not os.path.exists(self.roadmap_dir):
            return artifacts

        for root, dirs, files in os.walk(self.roadmap_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, self.roadmap_dir)
                artifacts.append(self._classify(rel_path, file_path))
        
        return artifacts

    def _classify(self, rel_path: str, full_path: str) -> CanonicalArtifact:
        file_name = os.path.basename(rel_path)
        stats = os.stat(full_path)
        last_mod = datetime.datetime.fromtimestamp(stats.st_mtime).isoformat()
        
        category = ArtifactCategory.SOURCE_OF_TRUTH
        role = ArtifactRole.GENERIC
        plugin_id = None

        # Logic for classification based on naming conventions
        if file_name == "activity.jsonl":
            role = ArtifactRole.ACTIVITY
        elif file_name == "roadmap.json":
            role = ArtifactRole.ROADMAP
            category = ArtifactCategory.PROJECTION
        elif file_name.startswith("roadmap.") and file_name.endswith(".json"):
            role = ArtifactRole.ROADMAP
            category = ArtifactCategory.PROJECTION
            plugin_id = file_name.split(".")[1]
        elif file_name == "issues.json":
            role = ArtifactRole.ISSUES
            category = ArtifactCategory.PROJECTION
        elif file_name == "lessons.json":
            role = ArtifactRole.LESSONS
            category = ArtifactCategory.PROJECTION
        elif "CONTRACT" in file_name:
            category = ArtifactCategory.CONTRACT
            role = ArtifactRole.ORCHESTRATOR_CONTRACT if "ORCHESTRATOR" in file_name else ArtifactRole.AGENT_CONTRACT
        elif "POLICY" in file_name:
            category = ArtifactCategory.POLICY
            role = ArtifactRole.RUNTIME_POLICY if "RUNTIME" in file_name else ArtifactRole.STORAGE_POLICY
        elif file_name.startswith("PARCER_PROFILE"):
            category = ArtifactCategory.PROFILE
            role = ArtifactRole.PARCER_PROFILE
        elif file_name.endswith(".schema.json"):
            category = ArtifactCategory.SCHEMA
            role = ArtifactRole.JSON_SCHEMA
        elif "swarm" in file_name.lower():
            category = ArtifactCategory.SWARM
            role = ArtifactRole.SWARM_CONFIG
        elif "snapshots" in rel_path:
            category = ArtifactCategory.SNAPSHOT

        return CanonicalArtifact(
            file_path=rel_path,
            file_name=file_name,
            category=category,
            role=role,
            plugin_id=plugin_id,
            last_modified=last_mod,
            size_bytes=stats.st_size
        )
