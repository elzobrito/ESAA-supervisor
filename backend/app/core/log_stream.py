import asyncio
from typing import Dict, List, AsyncGenerator
from app.models.run_state import RunLogEntry

class LogStreamer:
    # Memory-based log buffer and queue for SSE.
    _logs: Dict[str, List[RunLogEntry]] = {}
    _queues: Dict[str, List[asyncio.Queue]] = {}

    @classmethod
    def add_log(cls, run_id: str, entry: RunLogEntry):
        if run_id not in cls._logs:
            cls._logs[run_id] = []
        cls._logs[run_id].append(entry)
        
        # Notify all active queues for this run
        if run_id in cls._queues:
            for q in cls._queues[run_id]:
                q.put_nowait(entry)

    @classmethod
    async def stream_logs(cls, run_id: str) -> AsyncGenerator[RunLogEntry, None]:
        queue = asyncio.Queue()
        if run_id not in cls._queues:
            cls._queues[run_id] = []
        cls._queues[run_id].append(queue)
        
        # Yield existing logs first
        if run_id in cls._logs:
            for entry in cls._logs[run_id]:
                yield entry

        try:
            while True:
                entry = await queue.get()
                yield entry
        finally:
            cls._queues[run_id].remove(queue)
            if not cls._queues[run_id]:
                del cls._queues[run_id]
