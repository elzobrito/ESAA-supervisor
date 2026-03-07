from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class ChatStore:
    def __init__(self, roadmap_dir: str):
        self.roadmap_dir = Path(roadmap_dir)
        self.sessions_dir = self.roadmap_dir / "chat_sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def list_sessions(self) -> list[dict[str, Any]]:
        sessions = [self.load_session(path.stem) for path in self.sessions_dir.glob("*.json")]
        sessions = [session for session in sessions if session is not None]
        return sorted(sessions, key=lambda item: item.get("updated_at", ""), reverse=True)

    def create_session(
        self,
        *,
        agent_id: str,
        mode: str,
        title: str | None = None,
        task_id: str | None = None,
        roadmap_id: str | None = None,
    ) -> dict[str, Any]:
        session = {
            "session_id": str(uuid.uuid4()),
            "agent_id": agent_id,
            "mode": mode,
            "title": title or ("Task chat" if mode == "task" else "New chat"),
            "task_id": task_id,
            "roadmap_id": roadmap_id,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "messages": [],
        }
        self.save_session(session)
        return session

    def load_session(self, session_id: str) -> dict[str, Any] | None:
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def save_session(self, session: dict[str, Any]) -> dict[str, Any]:
        session["updated_at"] = utc_now_iso()
        path = self.sessions_dir / f"{session['session_id']}.json"
        path.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return session

    def delete_session(self, session_id: str) -> bool:
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            return False
        path.unlink()
        return True

    def append_message(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = self.load_session(session_id)
        if session is None:
            raise FileNotFoundError(session_id)
        message = {
            "message_id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "created_at": utc_now_iso(),
            "metadata": metadata or {},
        }
        session.setdefault("messages", []).append(message)
        if session.get("title") in {"New chat", "Task chat"} and role == "user":
            session["title"] = content.strip().splitlines()[0][:72] or session["title"]
        self.save_session(session)
        return session
