from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.routes_projects import store
from app.api.routes_state import _load_roadmap_variants
from app.api.schemas import IntegrityRepairRequest, IntegrityRepairResponse
from app.core.artifact_discovery import ArtifactDiscovery
from app.core.projector import Projector
from app.core.validators import ArtifactValidator

router = APIRouter(prefix="/projects/{project_id}/integrity", tags=["integrity"])


def _get_project_roadmap_dir(project_id: str) -> str:
    if not store.active_project or store.active_project.id != project_id:
        raise HTTPException(status_code=404, detail="Project not active. Call GET /projects first.")
    return store.active_project.base_path


def _repair_roadmap_hash(roadmap_dir: str, roadmap_id: str) -> bool:
    roadmap_path = Path(roadmap_dir) / roadmap_id
    if not roadmap_path.exists():
        return False

    roadmap = json.loads(roadmap_path.read_text(encoding="utf-8"))
    roadmap.setdefault("meta", {}).setdefault("run", {})
    roadmap["meta"]["run"]["projection_hash_sha256"] = Projector.compute_projection_hash(roadmap)
    roadmap["meta"]["run"]["verify_status"] = "ok"
    roadmap["meta"]["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    roadmap_path.write_text(json.dumps(roadmap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


@router.post("/repair", response_model=IntegrityRepairResponse)
async def repair_integrity(project_id: str, request: IntegrityRepairRequest):
    roadmap_dir = _get_project_roadmap_dir(project_id)
    variants = _load_roadmap_variants(roadmap_dir)
    if not variants:
        raise HTTPException(status_code=404, detail="No roadmap files found for project.")

    target_ids = [request.roadmap_id] if request.roadmap_id else list(variants.keys())
    repaired: list[str] = []
    for roadmap_id in target_ids:
        if roadmap_id not in variants:
            raise HTTPException(status_code=404, detail=f"Requested roadmap not found: {roadmap_id}")
        if _repair_roadmap_hash(roadmap_dir, roadmap_id):
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
        artifact_issues_after=artifact_issues_after,
        is_consistent=raw.is_consistent,
        message="Integrity metadata refreshed and artifacts revalidated.",
    )
