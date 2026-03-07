from typing import Dict, Optional

class ProjectLock:
    # Simplified memory-based lock for PoC.
    # In a real app, this could use file locks or Redis.
    _locks: Dict[str, str] = {}  # project_id -> run_id

    @classmethod
    def acquire(cls, project_id: str, run_id: str) -> bool:
        if project_id in cls._locks:
            return False
        cls._locks[project_id] = run_id
        return True

    @classmethod
    def release(cls, project_id: str, run_id: str):
        if cls._locks.get(project_id) == run_id:
            del cls._locks[project_id]

    @classmethod
    def is_locked(cls, project_id: str) -> bool:
        return project_id in cls._locks

    @classmethod
    def get_holder(cls, project_id: str) -> Optional[str]:
        return cls._locks.get(project_id)
