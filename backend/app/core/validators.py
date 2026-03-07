import os
from typing import Dict, Any

from app.core.schema_validation import validate_json_structure, validate_schema, validate_yaml_structure
from app.core.encoding_checks import check_encoding, detect_mojibake
from app.models.canonical_artifact import CanonicalArtifact
from app.utils.jsonl import read_jsonl


class ArtifactValidator:
    def __init__(self, roadmap_dir: str):
        self.roadmap_dir = roadmap_dir

    def validate(self, artifact: CanonicalArtifact) -> Dict[str, Any]:
        full_path = os.path.join(self.roadmap_dir, artifact.file_path)
        result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }

        # 1. Encoding check
        if not check_encoding(full_path):
            result["is_valid"] = False
            result["errors"].append("Invalid encoding: File must be UTF-8")
            return result

        # 2. Content validation based on extension
        ext = os.path.splitext(artifact.file_name)[1].lower()
        
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        if ext == ".json":
            is_ok, err, data = validate_json_structure(content)
            if not is_ok:
                result["is_valid"] = False
                result["errors"].append(f"JSON Parse Error: {err}")
            elif detect_mojibake(content):
                result["warnings"].append("Possible mojibake detected in JSON content")
            elif artifact.file_name.endswith(".schema.json"):
                # Schema artifacts are sources of validation rules, not projection instances.
                pass
            else:
                schema_path = self._resolve_schema_path(artifact.file_name)
                if schema_path:
                    schema_ok, schema_err = validate_schema(data, schema_path)
                    if not schema_ok:
                        result["is_valid"] = False
                        result["errors"].append(f"JSON Schema Error: {schema_err}")

        elif ext == ".yaml" or ext == ".yml":
            is_ok, err, data = validate_yaml_structure(content)
            if not is_ok:
                result["is_valid"] = False
                result["errors"].append(f"YAML Parse Error: {err}")

        elif ext == ".jsonl":
            try:
                read_jsonl(full_path)
            except Exception as e:
                result["is_valid"] = False
                result["errors"].append(f"JSONL Parse Error: {str(e)}")

        return result

    def _resolve_schema_path(self, file_name: str) -> str | None:
        candidates = []
        stem, _ = os.path.splitext(file_name)
        candidates.append(os.path.join(self.roadmap_dir, f"{stem}.schema.json"))
        if stem.startswith("roadmap."):
            candidates.append(os.path.join(self.roadmap_dir, "roadmap.schema.json"))

        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        return None
