import json
from pathlib import Path

from app.core.validators import ArtifactValidator
from app.models.canonical_artifact import CanonicalArtifact, ArtifactCategory, ArtifactRole


def _make_artifact(tmp_path: Path, filename: str, content: str) -> CanonicalArtifact:
    (tmp_path / filename).write_text(content, encoding="utf-8")
    return CanonicalArtifact(
        file_path=filename,
        file_name=filename,
        category=ArtifactCategory.PROJECTION,
        role=ArtifactRole.ROADMAP,
        last_modified="2026-01-01T00:00:00",
        size_bytes=len(content.encode()),
    )


def test_valid_json_passes(tmp_path: Path) -> None:
    artifact = _make_artifact(tmp_path, "roadmap.json", json.dumps({"tasks": []}))
    result = ArtifactValidator(str(tmp_path)).validate(artifact)
    assert result["is_valid"] is True
    assert result["errors"] == []


def test_invalid_json_fails(tmp_path: Path) -> None:
    artifact = _make_artifact(tmp_path, "roadmap.json", "{invalid json}")
    result = ArtifactValidator(str(tmp_path)).validate(artifact)
    assert result["is_valid"] is False
    assert any("JSON" in e for e in result["errors"])


def test_valid_jsonl_passes(tmp_path: Path) -> None:
    content = json.dumps({"event_seq": 1}) + "\n" + json.dumps({"event_seq": 2}) + "\n"
    artifact = _make_artifact(tmp_path, "activity.jsonl", content)
    artifact = artifact.model_copy(update={"role": ArtifactRole.ACTIVITY})
    result = ArtifactValidator(str(tmp_path)).validate(artifact)
    assert result["is_valid"] is True


def test_invalid_jsonl_fails(tmp_path: Path) -> None:
    content = json.dumps({"event_seq": 1}) + "\n" + "NOT JSON\n"
    artifact = _make_artifact(tmp_path, "activity.jsonl", content)
    artifact = artifact.model_copy(update={"role": ArtifactRole.ACTIVITY})
    result = ArtifactValidator(str(tmp_path)).validate(artifact)
    assert result["is_valid"] is False
    assert any("JSONL" in e for e in result["errors"])


def test_valid_yaml_passes(tmp_path: Path) -> None:
    content = "name: agent-impl\nversion: 1\n"
    (tmp_path / "profile.yaml").write_text(content, encoding="utf-8")
    artifact = CanonicalArtifact(
        file_path="profile.yaml",
        file_name="profile.yaml",
        category=ArtifactCategory.PROFILE,
        role=ArtifactRole.PARCER_PROFILE,
        last_modified="2026-01-01T00:00:00",
        size_bytes=len(content.encode()),
    )
    result = ArtifactValidator(str(tmp_path)).validate(artifact)
    assert result["is_valid"] is True


def test_invalid_yaml_fails(tmp_path: Path) -> None:
    content = "name: [\nbad yaml"
    (tmp_path / "profile.yaml").write_text(content, encoding="utf-8")
    artifact = CanonicalArtifact(
        file_path="profile.yaml",
        file_name="profile.yaml",
        category=ArtifactCategory.PROFILE,
        role=ArtifactRole.PARCER_PROFILE,
        last_modified="2026-01-01T00:00:00",
        size_bytes=len(content.encode()),
    )
    result = ArtifactValidator(str(tmp_path)).validate(artifact)
    assert result["is_valid"] is False
    assert any("YAML" in e for e in result["errors"])


def test_json_schema_is_applied_when_present(tmp_path: Path) -> None:
    (tmp_path / "roadmap.schema.json").write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["tasks"],
                "properties": {
                    "tasks": {"type": "array"},
                },
            }
        ),
        encoding="utf-8",
    )
    artifact = _make_artifact(tmp_path, "roadmap.json", json.dumps({"foo": []}))

    result = ArtifactValidator(str(tmp_path)).validate(artifact)

    assert result["is_valid"] is False
    assert any("Schema" in e for e in result["errors"])
