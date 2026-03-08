from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FALLBACK_ENCODINGS = ("cp1252", "latin-1")


@dataclass(slots=True)
class JsonArtifactLoadResult:
    path: Path
    payload: Any
    encoding_used: str
    is_fallback: bool
    warning: str | None = None


class JsonArtifactLoadError(RuntimeError):
    def __init__(self, path: str | Path, message: str):
        self.path = Path(path)
        super().__init__(message)


def load_json_artifact(path: str | Path) -> JsonArtifactLoadResult:
    artifact_path = Path(path)
    raw = artifact_path.read_bytes()

    for encoding in ("utf-8", *FALLBACK_ENCODINGS):
        try:
            content = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise JsonArtifactLoadError(artifact_path, f"Invalid JSON in {artifact_path.name}: {exc}") from exc
        is_fallback = encoding != "utf-8"
        warning = None
        if is_fallback:
            warning = f"{artifact_path.name} loaded using fallback encoding {encoding}. Normalize it via Repair Integrity."
        return JsonArtifactLoadResult(
            path=artifact_path,
            payload=payload,
            encoding_used=encoding,
            is_fallback=is_fallback,
            warning=warning,
        )

    raise JsonArtifactLoadError(
        artifact_path,
        f"{artifact_path.name} could not be decoded as UTF-8, cp1252 or latin-1.",
    )


def write_json_artifact(path: str | Path, payload: Any) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
