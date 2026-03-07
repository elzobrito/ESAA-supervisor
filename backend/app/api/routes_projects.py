import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pathlib import Path

from app.api.schemas import ArtifactContentResponse, FileSystemEntryResponse, OpenProjectRequest, ProjectBrowserResponse, ProjectFileBrowserResponse, ProjectFileEntryResponse, ProjectResponse
from app.core.canonical_store import CanonicalStore

router = APIRouter(prefix="/projects", tags=["projects"])

WORKSPACE_ROOT = os.path.abspath("..")
ROADMAP_DIR = os.path.join(WORKSPACE_ROOT, ".roadmap")
DRIVE, _ = os.path.splitdrive(WORKSPACE_ROOT)
BROWSE_ROOT = f"{DRIVE}{os.sep}" if DRIVE else os.path.abspath(os.sep)
DISCOVERY_ROOT = os.path.abspath(os.path.join(WORKSPACE_ROOT, ".."))
MAX_DISCOVERY_DEPTH = 4
MAX_ARTIFACT_PREVIEW_BYTES = 262144
MAX_ARTIFACT_FULL_BYTES = 2097152
store = CanonicalStore(WORKSPACE_ROOT)


def _normalize_browse_path(path: Optional[str]) -> str:
    target = os.path.abspath(path or BROWSE_ROOT)
    if os.path.commonpath([BROWSE_ROOT, target]) != BROWSE_ROOT:
        raise HTTPException(status_code=400, detail="Path outside allowed browse root.")
    if not os.path.isdir(target):
        raise HTTPException(status_code=404, detail="Directory not found.")
    return target


def _resolve_project_dir(selected_path: str) -> tuple[str, str, str]:
    target = _normalize_browse_path(selected_path)
    roadmap_dir = target if os.path.basename(target) == ".roadmap" else os.path.join(target, ".roadmap")
    roadmap_file = os.path.join(roadmap_dir, "roadmap.json")
    if not os.path.exists(roadmap_file):
        raise HTTPException(status_code=400, detail="Selected folder is not a project with .roadmap/roadmap.json.")
    project_root = os.path.dirname(roadmap_dir)
    project_id = os.path.basename(project_root)
    return project_id, project_root, roadmap_dir


def _project_response(project_id: str, project_root: str, roadmap_dir: str, *, is_active: bool) -> ProjectResponse:
    return ProjectResponse(
        id=project_id,
        name=os.path.basename(project_root),
        base_path=roadmap_dir,
        project_path=project_root,
        is_active=is_active,
    )


def _active_project_root(project_id: str) -> Path:
    if not store.active_project or store.active_project.id != project_id:
        raise HTTPException(status_code=404, detail="Project not found.")
    return Path(store.active_project.base_path).parent.resolve()


def _resolve_artifact_path(project_id: str, artifact_path: str) -> Path:
    project_root = _active_project_root(project_id)
    roadmap_root = Path(store.active_project.base_path).resolve()
    candidate = Path(artifact_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        project_candidate = (project_root / candidate).resolve()
        roadmap_candidate = (roadmap_root / candidate).resolve()
        if project_candidate.exists():
            resolved = project_candidate
        elif roadmap_candidate.exists():
            resolved = roadmap_candidate
        else:
            resolved = project_candidate
    if not (
        resolved.is_relative_to(project_root)
        or resolved.is_relative_to(roadmap_root)
    ):
        raise HTTPException(status_code=400, detail="Artifact path is outside the active project.")
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Artifact file not found.")
    return resolved


def _resolve_project_browse_path(project_id: str, browse_path: Optional[str]) -> Path:
    project_root = _active_project_root(project_id)
    if not browse_path:
        return project_root
    candidate = Path(browse_path)
    resolved = candidate.resolve() if candidate.is_absolute() else (project_root / candidate).resolve()
    if not resolved.is_relative_to(project_root):
        raise HTTPException(status_code=400, detail="Browse path is outside the active project.")
    if not resolved.exists() or not resolved.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found.")
    return resolved


def _discover_projects(root_path: str, max_depth: int = MAX_DISCOVERY_DEPTH) -> list[ProjectResponse]:
    projects: list[ProjectResponse] = []
    seen: set[str] = set()
    normalized_root = _normalize_browse_path(root_path)
    root_depth = normalized_root.rstrip(os.sep).count(os.sep)

    for current_root, dirs, _ in os.walk(normalized_root):
        current_depth = current_root.rstrip(os.sep).count(os.sep) - root_depth
        if current_depth > max_depth:
            dirs[:] = []
            continue

        roadmap_file = os.path.join(current_root, ".roadmap", "roadmap.json")
        if os.path.exists(roadmap_file):
            roadmap_dir = os.path.join(current_root, ".roadmap")
            if roadmap_dir not in seen:
                seen.add(roadmap_dir)
                project_id = os.path.basename(current_root)
                is_active = bool(store.active_project and store.active_project.base_path == roadmap_dir)
                projects.append(_project_response(project_id, current_root, roadmap_dir, is_active=is_active))
            dirs[:] = [directory for directory in dirs if directory != ".roadmap"]

    return projects


@router.get("", response_model=List[ProjectResponse])
async def list_projects():
    projects = _discover_projects(DISCOVERY_ROOT, max_depth=2)
    if not projects and os.path.exists(os.path.join(ROADMAP_DIR, "roadmap.json")):
        store.load_project("ESAA-supervisor", ROADMAP_DIR)
        projects = [_project_response("ESAA-supervisor", WORKSPACE_ROOT, ROADMAP_DIR, is_active=True)]
    return projects


@router.get("/browse", response_model=ProjectBrowserResponse)
async def browse_projects(path: Optional[str] = Query(default=None)):
    current_path = _normalize_browse_path(path)
    parent_path = None if current_path == BROWSE_ROOT else os.path.dirname(current_path)

    directories = [
        FileSystemEntryResponse(name=entry.name, path=entry.path)
        for entry in sorted(os.scandir(current_path), key=lambda item: item.name.lower())
        if entry.is_dir() and entry.name != ".roadmap"
    ]

    projects: list[ProjectResponse] = []
    if os.path.exists(os.path.join(current_path, ".roadmap", "roadmap.json")):
        project_id, project_root, roadmap_dir = _resolve_project_dir(current_path)
        is_active = bool(store.active_project and store.active_project.base_path == roadmap_dir)
        projects.append(_project_response(project_id, project_root, roadmap_dir, is_active=is_active))

    for entry in directories:
        roadmap_file = os.path.join(entry.path, ".roadmap", "roadmap.json")
        if os.path.exists(roadmap_file):
            project_id, project_root, roadmap_dir = _resolve_project_dir(entry.path)
            is_active = bool(store.active_project and store.active_project.base_path == roadmap_dir)
            projects.append(_project_response(project_id, project_root, roadmap_dir, is_active=is_active))

    return ProjectBrowserResponse(
        current_path=current_path,
        parent_path=parent_path if parent_path and os.path.commonpath([BROWSE_ROOT, parent_path]) == BROWSE_ROOT else None,
        directories=directories,
        projects=projects,
    )


@router.post("/open", response_model=ProjectResponse)
async def open_project(request: OpenProjectRequest):
    project_id, project_root, roadmap_dir = _resolve_project_dir(request.path)
    store.load_project(project_id, roadmap_dir)
    return _project_response(project_id, project_root, roadmap_dir, is_active=True)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    if store.active_project and store.active_project.id == project_id:
        project_root = os.path.dirname(store.active_project.base_path)
        return _project_response(project_id, project_root, store.active_project.base_path, is_active=True)

    for project in _discover_projects(DISCOVERY_ROOT, max_depth=3):
        if project.id == project_id:
            store.load_project(project.id, project.base_path)
            return _project_response(project.id, project.project_path or os.path.dirname(project.base_path), project.base_path, is_active=True)

    raise HTTPException(status_code=404, detail="Project not found.")


@router.get("/{project_id}/artifacts/content", response_model=ArtifactContentResponse)
async def read_artifact_content(project_id: str, path: str = Query(...), full: bool = Query(default=False)):
    artifact_path = _resolve_artifact_path(project_id, path)
    raw = artifact_path.read_bytes()
    limit = MAX_ARTIFACT_FULL_BYTES if full else MAX_ARTIFACT_PREVIEW_BYTES
    truncated = len(raw) > limit
    preview_bytes = raw[:limit]
    try:
        content = preview_bytes.decode("utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        content = preview_bytes.decode("utf-8", errors="replace")
        encoding = "utf-8-replace"

    return ArtifactContentResponse(
        path=str(artifact_path),
        content=content,
        truncated=truncated,
        encoding=encoding,
        size_bytes=len(raw),
    )


@router.get("/{project_id}/files/browse", response_model=ProjectFileBrowserResponse)
async def browse_project_files(project_id: str, path: Optional[str] = Query(default=None)):
    current_dir = _resolve_project_browse_path(project_id, path)
    project_root = _active_project_root(project_id)
    parent_path = None if current_dir == project_root else str(current_dir.parent.relative_to(project_root))

    directories: list[ProjectFileEntryResponse] = []
    files: list[ProjectFileEntryResponse] = []
    for entry in sorted(current_dir.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        rel_path = str(entry.relative_to(project_root))
        item = ProjectFileEntryResponse(
            name=entry.name,
            path=rel_path,
            kind="directory" if entry.is_dir() else "file",
        )
        if entry.is_dir():
            directories.append(item)
        else:
            files.append(item)

    return ProjectFileBrowserResponse(
        current_path=str(current_dir.relative_to(project_root)) if current_dir != project_root else "",
        parent_path=parent_path,
        directories=directories,
        files=files,
    )
