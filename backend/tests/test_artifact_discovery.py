import json
from pathlib import Path

from app.core.artifact_discovery import ArtifactDiscovery
from app.models.canonical_artifact import ArtifactCategory, ArtifactRole


def _touch(path: Path, content: str = "{}") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_discovers_core_projections(tmp_path: Path) -> None:
    _touch(tmp_path / "activity.jsonl", "{}\n")
    _touch(tmp_path / "roadmap.json")
    _touch(tmp_path / "issues.json")
    _touch(tmp_path / "lessons.json")

    artifacts = ArtifactDiscovery(str(tmp_path)).discover()
    roles = {a.role for a in artifacts}

    assert ArtifactRole.ACTIVITY in roles
    assert ArtifactRole.ROADMAP in roles
    assert ArtifactRole.ISSUES in roles
    assert ArtifactRole.LESSONS in roles


def test_classifies_roadmap_plugin(tmp_path: Path) -> None:
    _touch(tmp_path / "roadmap.myplugin.json")

    artifacts = ArtifactDiscovery(str(tmp_path)).discover()
    plugin_artifacts = [a for a in artifacts if a.plugin_id == "myPlugin" or a.role == ArtifactRole.ROADMAP]

    assert len(plugin_artifacts) == 1
    assert plugin_artifacts[0].category == ArtifactCategory.PROJECTION


def test_classifies_parcer_profile(tmp_path: Path) -> None:
    _touch(tmp_path / "PARCER_PROFILE.agent-impl.yaml", "name: agent-impl\n")

    artifacts = ArtifactDiscovery(str(tmp_path)).discover()
    profiles = [a for a in artifacts if a.role == ArtifactRole.PARCER_PROFILE]

    assert len(profiles) == 1
    assert profiles[0].category == ArtifactCategory.PROFILE


def test_classifies_schema(tmp_path: Path) -> None:
    _touch(tmp_path / "agent_result.schema.json")

    artifacts = ArtifactDiscovery(str(tmp_path)).discover()
    schemas = [a for a in artifacts if a.role == ArtifactRole.JSON_SCHEMA]

    assert len(schemas) == 1
    assert schemas[0].category == ArtifactCategory.SCHEMA


def test_classifies_contracts(tmp_path: Path) -> None:
    _touch(tmp_path / "ORCHESTRATOR_CONTRACT.yaml", "name: orc\n")
    _touch(tmp_path / "AGENT_CONTRACT.yaml", "name: agent\n")

    artifacts = ArtifactDiscovery(str(tmp_path)).discover()
    contracts = {a.role for a in artifacts if a.category == ArtifactCategory.CONTRACT}

    assert ArtifactRole.ORCHESTRATOR_CONTRACT in contracts
    assert ArtifactRole.AGENT_CONTRACT in contracts


def test_returns_empty_for_nonexistent_dir() -> None:
    artifacts = ArtifactDiscovery("/nonexistent/path/xyz").discover()
    assert artifacts == []
