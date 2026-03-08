from __future__ import annotations

from datetime import datetime, timezone
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.routes_projects import store
from app.api.routes_state import _discover_roadmap_variants
from app.api.schemas import IntegrityRepairRequest, IntegrityRepairResponse
from app.core.artifact_discovery import ArtifactDiscovery
from app.core.projector import Projector
from app.core.validators import ArtifactValidator
from app.utils.json_artifacts import JsonArtifactLoadError, load_json_artifact, write_json_artifact
from app.utils.jsonl import read_jsonl

router = APIRouter(prefix="/projects/{project_id}/integrity", tags=["integrity"])


def _get_project_roadmap_dir(project_id: str) -> str:
    if not store.active_project or store.active_project.id != project_id:
        raise HTTPException(status_code=404, detail="Project not active. Call GET /projects first.")
    return store.active_project.base_path


def _repair_roadmap_projection(roadmap_dir: str, roadmap_id: str) -> bool:
    roadmap_path = Path(roadmap_dir) / roadmap_id
    if not roadmap_path.exists():
        return False

    projector = Projector(roadmap_dir, roadmap_id=roadmap_id)
    result = projector.reconcile_activity_tail_to_disk()
    if result["is_consistent"]:
        projector.sync_to_disk([])
        return True
    if result["invalid_event"] is None:
        return False
    if not _trust_current_projection(roadmap_dir, roadmap_id):
        return False
    projector.sync_to_disk([])
    return True


def _trust_current_projection(roadmap_dir: str, roadmap_id: str) -> bool:
    roadmap_path = Path(roadmap_dir) / roadmap_id
    try:
        roadmap = load_json_artifact(roadmap_path).payload
    except JsonArtifactLoadError:
        return False

    run_meta = roadmap.setdefault("meta", {}).setdefault("run", {})
    stored_hash = run_meta.get("projection_hash_sha256")
    if not stored_hash:
        return False

    try:
        computed_hash = Projector.compute_projection_hash(roadmap)
    except Exception:
        return False
    if computed_hash != stored_hash:
        return False

    max_event_seq = max(
        (int(event.get("event_seq", 0) or 0) for event in read_jsonl(str(Path(roadmap_dir) / "activity.jsonl"))),
        default=int(run_meta.get("last_event_seq", 0) or 0),
    )
    run_meta["last_event_seq"] = max_event_seq
    run_meta["verify_status"] = "ok"
    run_meta.pop("integrity_error", None)
    roadmap["meta"]["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    write_json_artifact(roadmap_path, roadmap)
    return True


def _create_encoding_snapshot(roadmap_dir: str, files: list[Path]) -> Path:
    snapshot_root = Path(roadmap_dir) / "snapshots" / f"encoding_repair_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    snapshot_root.mkdir(parents=True, exist_ok=True)
    for file_path in files:
        if not file_path.exists():
            continue
        shutil.copy2(file_path, snapshot_root / file_path.name)
    return snapshot_root


def _normalize_json_artifacts(roadmap_dir: str, roadmap_ids: list[str]) -> tuple[list[str], list[str]]:
    candidate_files = [Path(roadmap_dir) / roadmap_id for roadmap_id in roadmap_ids]
    candidate_files.extend(
        [
            Path(roadmap_dir) / "issues.json",
            Path(roadmap_dir) / "lessons.json",
        ]
    )
    existing_files = [path for path in candidate_files if path.exists()]
    normalized: list[str] = []
    unrecoverable: list[str] = []
    fallback_loaded: list[tuple[Path, object]] = []

    for file_path in existing_files:
        try:
            loaded = load_json_artifact(file_path)
        except JsonArtifactLoadError:
            unrecoverable.append(file_path.name)
            continue
        if loaded.is_fallback:
            fallback_loaded.append((file_path, loaded.payload))

    if fallback_loaded:
        _create_encoding_snapshot(roadmap_dir, [item[0] for item in fallback_loaded])
        for file_path, payload in fallback_loaded:
            write_json_artifact(file_path, payload)
            normalized.append(file_path.name)

    return normalized, unrecoverable


@router.post("/repair", response_model=IntegrityRepairResponse)
async def repair_integrity(project_id: str, request: IntegrityRepairRequest):
    roadmap_dir = _get_project_roadmap_dir(project_id)
    variants = _discover_roadmap_variants(roadmap_dir)
    if not variants:
        raise HTTPException(status_code=404, detail="No roadmap files found for project.")

    target_ids = [request.roadmap_id] if request.roadmap_id else list(variants.keys())
    normalized_files, unrecoverable_files = _normalize_json_artifacts(roadmap_dir, target_ids)
    variants = _discover_roadmap_variants(roadmap_dir)
    repaired: list[str] = []
    for roadmap_id in target_ids:
        if roadmap_id not in variants:
            raise HTTPException(status_code=404, detail=f"Requested roadmap not found: {roadmap_id}")
        if variants[roadmap_id].get("payload") is None:
            unrecoverable_files.append(roadmap_id)
            continue
        if _repair_roadmap_projection(roadmap_dir, roadmap_id):
            repaired.append(roadmap_id)

    validator = ArtifactValidator(roadmap_dir)
    artifact_issues_after = sum(
        1
        for artifact in ArtifactDiscovery(roadmap_dir).discover()
        if not validator.validate(artifact)["is_valid"]
    )

    store.load_project(project_id, roadmap_dir)
    raw = store.get_state()

    return IntegrityRepairResponse(
        repaired_roadmaps=repaired,
        normalized_files=normalized_files,
        unrecoverable_files=sorted(set(unrecoverable_files)),
        artifact_issues_after=artifact_issues_after,
        is_consistent=raw.is_consistent,
        message="Integrity metadata refreshed, canonical JSON normalized when recoverable, and artifacts revalidated.",
    )
