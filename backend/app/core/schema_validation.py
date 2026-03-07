import json
from pathlib import Path
from typing import Any, Optional, Tuple

import yaml

def validate_json_structure(content: str) -> Tuple[bool, Optional[str], Optional[Any]]:
    try:
        data = json.loads(content)
        return True, None, data
    except json.JSONDecodeError as e:
        return False, str(e), None

def validate_yaml_structure(content: str) -> Tuple[bool, Optional[str], Optional[Any]]:
    try:
        data = yaml.safe_load(content)
        return True, None, data
    except yaml.YAMLError as e:
        return False, str(e), None

def validate_schema(data: Any, schema_path: str) -> Tuple[bool, Optional[str]]:
    path = Path(schema_path)
    if not path.exists():
        return False, f"Schema file not found: {schema_path}"

    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"Invalid schema file: {exc}"

    try:
        _validate_against_schema(data, schema, path="$")
    except ValueError as exc:
        return False, str(exc)

    return True, None


def _validate_against_schema(data: Any, schema: dict[str, Any], *, path: str) -> None:
    expected_type = schema.get("type")
    if expected_type:
        if expected_type == "object":
            if not isinstance(data, dict):
                raise ValueError(f"{path}: expected object")
            required = schema.get("required", [])
            for key in required:
                if key not in data:
                    raise ValueError(f"{path}: missing required property '{key}'")
            for key, value in data.items():
                child_schema = schema.get("properties", {}).get(key)
                if child_schema:
                    _validate_against_schema(value, child_schema, path=f"{path}.{key}")
            return

        if expected_type == "array":
            if not isinstance(data, list):
                raise ValueError(f"{path}: expected array")
            item_schema = schema.get("items")
            if item_schema:
                for index, item in enumerate(data):
                    _validate_against_schema(item, item_schema, path=f"{path}[{index}]")
            return

        if not _matches_scalar_type(data, expected_type):
            raise ValueError(f"{path}: expected {expected_type}")


def _matches_scalar_type(value: Any, expected_type: str) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return True
