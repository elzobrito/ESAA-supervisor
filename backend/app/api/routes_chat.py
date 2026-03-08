from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.api.routes_projects import store
from app.api.routes_state import _discover_roadmap_variants
from app.api.schemas import (
    ChatCreateRequest,
    ChatMessageCreateRequest,
    ChatMessageResponse,
    ChatSessionDetailResponse,
    ChatSessionMutationResponse,
    ChatSessionResponse,
)
from app.core.chat_service import ChatService
from app.core.chat_store import ChatStore

router = APIRouter(prefix="/projects/{project_id}/chat", tags=["chat"])


def _get_project_context(project_id: str) -> tuple[str, str]:
    if not store.active_project or store.active_project.id != project_id:
        raise HTTPException(status_code=404, detail="Project not active. Call GET /projects first.")
    roadmap_dir = store.active_project.base_path
    workspace_root = str(Path(store.active_project.base_path).parent)
    return roadmap_dir, workspace_root


def _build_message_response(message: dict) -> ChatMessageResponse:
    return ChatMessageResponse(
        message_id=message["message_id"],
        role=message["role"],
        content=message["content"],
        created_at=message["created_at"],
        metadata=message.get("metadata", {}),
    )


def _build_session_response(session: dict) -> ChatSessionResponse:
    return ChatSessionResponse(
        session_id=session["session_id"],
        title=session["title"],
        agent_id=session["agent_id"],
        mode=session["mode"],
        task_id=session.get("task_id"),
        roadmap_id=session.get("roadmap_id"),
        created_at=session["created_at"],
        updated_at=session["updated_at"],
        message_count=len(session.get("messages", [])),
        last_message=session.get("messages", [])[-1]["content"] if session.get("messages") else None,
    )


def _resolve_task_context(roadmap_dir: str, roadmap_id: str | None, task_id: str | None) -> dict | None:
    if not task_id:
        return None
    selected_roadmap_id = roadmap_id or "roadmap.json"
    variants = _discover_roadmap_variants(roadmap_dir)
    roadmap_entry = variants.get(selected_roadmap_id)
    if not roadmap_entry:
        raise HTTPException(status_code=404, detail="Requested roadmap not found.")
    if roadmap_entry.get("payload") is None:
        raise HTTPException(status_code=409, detail=roadmap_entry.get("load_warning") or "Requested roadmap could not be loaded.")
    roadmap = roadmap_entry["payload"]
    task = next((item for item in roadmap.get("tasks", []) if item.get("task_id") == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found for chat session.")
    return task


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_chat_sessions(project_id: str):
    roadmap_dir, _ = _get_project_context(project_id)
    chat_store = ChatStore(roadmap_dir)
    return [_build_session_response(session) for session in chat_store.list_sessions()]


@router.post("/sessions", response_model=ChatSessionDetailResponse)
async def create_chat_session(project_id: str, request: ChatCreateRequest):
    roadmap_dir, _ = _get_project_context(project_id)
    task_context = _resolve_task_context(roadmap_dir, request.roadmap_id, request.task_id) if request.mode == "task" else None
    chat_store = ChatStore(roadmap_dir)
    title = request.title or (task_context.get("title") if task_context else None)
    session = chat_store.create_session(
        agent_id=request.agent_id,
        mode=request.mode,
        title=title,
        task_id=request.task_id,
        roadmap_id=request.roadmap_id,
    )
    return ChatSessionDetailResponse(
        **_build_session_response(session).model_dump(),
        messages=[],
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_chat_session(project_id: str, session_id: str):
    roadmap_dir, _ = _get_project_context(project_id)
    chat_store = ChatStore(roadmap_dir)
    session = chat_store.load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return ChatSessionDetailResponse(
        **_build_session_response(session).model_dump(),
        messages=[_build_message_response(message) for message in session.get("messages", [])],
    )


@router.delete("/sessions/{session_id}", response_model=ChatSessionMutationResponse)
async def delete_chat_session(project_id: str, session_id: str):
    roadmap_dir, _ = _get_project_context(project_id)
    chat_store = ChatStore(roadmap_dir)
    deleted = chat_store.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return ChatSessionMutationResponse(
        session_id=session_id,
        deleted=True,
        message="Chat session deleted.",
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatSessionDetailResponse)
async def send_chat_message(project_id: str, session_id: str, request: ChatMessageCreateRequest):
    roadmap_dir, workspace_root = _get_project_context(project_id)
    chat_store = ChatStore(roadmap_dir)
    session = chat_store.load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    task_context = _resolve_task_context(roadmap_dir, session.get("roadmap_id"), session.get("task_id")) if session.get("mode") == "task" else None
    session = chat_store.append_message(session_id, role="user", content=request.content)
    chat_result = ChatService().send_message(
        workspace_root=workspace_root,
        session=session,
        user_message=request.content,
        task_context=task_context,
    )
    session = chat_store.append_message(
        session_id,
        role="assistant",
        content=chat_result["content"],
        metadata=chat_result.get("metadata", {}),
    )

    return ChatSessionDetailResponse(
        **_build_session_response(session).model_dump(),
        messages=[_build_message_response(message) for message in session.get("messages", [])],
    )
