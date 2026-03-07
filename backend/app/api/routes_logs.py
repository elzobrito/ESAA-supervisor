from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse
from app.core.log_stream import LogStreamer
import json

router = APIRouter(prefix="/projects/{project_id}/logs", tags=["logs"])

@router.get("/stream/{run_id}")
async def stream_run_logs(project_id: str, run_id: str, request: Request):
    async def event_generator():
        async for log_entry in LogStreamer.stream_logs(run_id):
            # If client closes connection, stop streaming
            if await request.is_disconnected():
                break
            
            yield {
                "event": "log",
                "data": log_entry.model_dump_json()
            }

    return EventSourceResponse(event_generator())
