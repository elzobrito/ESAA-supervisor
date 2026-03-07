from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routes_projects import router as projects_router
from app.api.routes_state import router as state_router
from app.api.routes_runs import router as runs_router
from app.api.routes_logs import router as logs_router
from app.api.routes_tasks import router as tasks_router
from app.api.routes_issues import router as issues_router
from app.api.routes_integrity import router as integrity_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize canonical store and discovery
    print("ESAA Supervisor PoC starting...")
    yield
    # Shutdown: Clean up resources
    print("ESAA Supervisor PoC shutting down...")

app = FastAPI(
    title="ESAA Supervisor PoC API",
    version="0.4.0-poc",
    lifespan=lifespan
)

# CORS configuration for local React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For POC only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "app": "ESAA Supervisor PoC",
        "version": "0.4.0-poc",
        "status": "running"
    }

# Include API Routers
app.include_router(projects_router, prefix="/api/v1")
app.include_router(state_router, prefix="/api/v1")
app.include_router(runs_router, prefix="/api/v1")
app.include_router(logs_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(issues_router, prefix="/api/v1")
app.include_router(integrity_router, prefix="/api/v1")
