# SEC-003 - Attack Surface Inventory

## Scope and evidence basis

Workspace: `C:\xampp\htdocs\ESAA-supervisor`
Depends on: SEC-001 (tech-stack-inventory.md), SEC-002 (architecture-map.md)
Enumerated from: `backend/app/main.py`, `backend/app/api/routes_*.py`, `frontend/src/services/*.ts`, `backend/app/adapters/base.py`

---

## 1. HTTP REST Endpoints (FastAPI, base prefix `/api/v1`)

All endpoints are served by Uvicorn on `127.0.0.1:8000` (default). CORS policy: `allow_origins=["*"]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`.

### 1.1 Root

| ID | Method | Path | Auth | Input | Mutation |
|----|--------|------|------|-------|----------|
| EP-001 | GET | `/` | None | — | No |

### 1.2 Projects (`/api/v1/projects`)

| ID | Method | Path | Auth | Input | Mutation | Notes |
|----|--------|------|------|-------|----------|-------|
| EP-010 | GET | `/api/v1/projects` | None | — | No | Discovers projects on disk by walking `DISCOVERY_ROOT` (parent of workspace) |
| EP-011 | GET | `/api/v1/projects/browse` | None | `?path=<abs_path>` (query) | No | Exposes filesystem directory listing; constrained to `BROWSE_ROOT` (drive root on Windows) |
| EP-012 | POST | `/api/v1/projects/open` | None | `{"path": "<abs_path>"}` (JSON body) | Yes (in-memory state) | Loads a project by filesystem path; path validated against `BROWSE_ROOT` |
| EP-013 | GET | `/api/v1/projects/{project_id}` | None | `project_id` (path param) | Yes (side-effect: auto-loads project) | Triggers project discovery and load if project_id matches |
| EP-014 | GET | `/api/v1/projects/{project_id}/artifacts/content` | None | `?path=<rel_or_abs>&full=bool` (query) | No | Reads arbitrary file within project root or `.roadmap` root; up to 2 MB |
| EP-015 | GET | `/api/v1/projects/{project_id}/files/browse` | None | `?path=<rel_path>` (query) | No | Lists directory contents within project root |

### 1.3 State (`/api/v1/projects/{project_id}/state`)

| ID | Method | Path | Auth | Input | Mutation |
|----|--------|------|------|-------|----------|
| EP-020 | GET | `/api/v1/projects/{project_id}/state` | None | `?roadmap=<roadmap_id>` (query) | No (read) |

Response exposes: task list with descriptions, open issues, lessons, artifact catalog with paths, full activity log (all events), agent availability (command paths), roadmap consistency flags.

### 1.4 Runs (`/api/v1/projects/{project_id}/runs`)

| ID | Method | Path | Auth | Input | Mutation |
|----|--------|------|------|-------|----------|
| EP-030 | GET | `/api/v1/projects/{project_id}/runs/eligibility` | None | — | No |
| EP-031 | POST | `/api/v1/projects/{project_id}/runs/next` | None | `{"agent_id": str, "roadmap_id": str}` | Yes — starts agent subprocess, writes events |
| EP-032 | POST | `/api/v1/projects/{project_id}/runs/task` | None | `{"task_id": str, "agent_id": str, "roadmap_id": str}` | Yes — starts agent subprocess for specific task |
| EP-033 | POST | `/api/v1/projects/{project_id}/runs/{run_id}/decision` | None | `{"decision": "apply"/"reject", "selected_action": str}` | Yes — persists canonical events, mutates roadmap on disk |
| EP-034 | DELETE | `/api/v1/projects/{project_id}/runs/{run_id}` | None | — | Yes — cancels run |
| EP-035 | GET | `/api/v1/projects/{project_id}/runs/{run_id}` | None | — | No |

### 1.5 Tasks (`/api/v1/projects/{project_id}/tasks`)

| ID | Method | Path | Auth | Input | Mutation |
|----|--------|------|------|-------|----------|
| EP-040 | POST | `/api/v1/projects/{project_id}/tasks/reset` | None | `{"task_id": str, "roadmap_id": str}` | Yes — appends event to `activity.jsonl`, reprojects roadmap |

### 1.6 Issues (`/api/v1/projects/{project_id}/issues`)

| ID | Method | Path | Auth | Input | Mutation |
|----|--------|------|------|-------|----------|
| EP-050 | POST | `/api/v1/projects/{project_id}/issues/resolve` | None | `{"issue_id": str, "resolution_summary": str}` | Yes — appends event to `activity.jsonl`, reprojects roadmap |

### 1.7 Integrity (`/api/v1/projects/{project_id}/integrity`)

| ID | Method | Path | Auth | Input | Mutation |
|----|--------|------|------|-------|----------|
| EP-060 | POST | `/api/v1/projects/{project_id}/integrity/repair` | None | `{"roadmap_id": str?}` | Yes — rewrites roadmap JSON files on disk |

---

## 2. Server-Sent Events (SSE)

| ID | Protocol | Path | Auth | Direction | Notes |
|----|----------|------|------|-----------|-------|
| SSE-001 | HTTP/SSE (EventSource) | `/api/v1/projects/{project_id}/logs/stream/{run_id}` | None | Server → Browser | Streams run logs (stdout/stderr of agent subprocess) in real time; no authentication, no authorization scoping beyond `project_id`+`run_id` path params |

Client URL hardcoded in `frontend/src/services/logStream.ts` to `http://localhost:8000`.

---

## 3. Frontend SPA Routes (React Router, browser-only)

No server-side rendering. Routes are local browser navigation; the attack surface is entirely the API calls they trigger.

| Route | API calls triggered |
|-------|---------------------|
| `/` | `GET /projects` |
| `/projects/browse` | `GET /projects/browse?path=...` |
| `/projects/:projectId/overview` | `GET /projects/:id/state` |
| `/projects/:projectId/tasks` | `GET /projects/:id/state` |
| `/projects/:projectId/runs` | `GET /projects/:id/runs/:runId`, `POST /runs/next`, `POST /runs/task`, `POST /runs/:id/decision`, `DELETE /runs/:id` |
| `/projects/:projectId/activity` | `GET /projects/:id/state` |
| `/projects/:projectId/artifacts` | `GET /projects/:id/state`, `GET /projects/:id/artifacts/content` |
| `/projects/:projectId/integrity` | `GET /projects/:id/state`, `POST /projects/:id/integrity/repair` |
| `/projects/:projectId/issues` | `GET /projects/:id/state`, `POST /projects/:id/issues/resolve` |
| `/projects/:projectId/lessons` | `GET /projects/:id/state` |

---

## 4. File System Interfaces

These are not network endpoints but represent surfaces where input enters the application from the filesystem.

| ID | Interface | Read/Write | Input source | Notes |
|----|-----------|------------|--------------|-------|
| FS-001 | `.roadmap/activity.jsonl` | Read + Append | Agent subprocess output (via EventWriter) | Source of truth for all projections; corruption here affects all state |
| FS-002 | `.roadmap/roadmap*.json` | Read + Write | Projector after event application; `integrity/repair` endpoint | Materialized task state; written by `Projector.sync_to_disk` and `repair_roadmap_hash` |
| FS-003 | `.roadmap/issues.json` | Read + Write | Projector | Materialized issue state |
| FS-004 | `.roadmap/lessons.json` | Read + Write | Projector | Materialized lesson state |
| FS-005 | Project file tree (read) | Read | `?path=` parameter in `artifacts/content` and `files/browse` endpoints | Constrained to project root and `.roadmap` root by `_resolve_artifact_path` |
| FS-006 | BROWSE_ROOT directory walk | Read | `?path=` parameter in `projects/browse` endpoint | Constrained to drive root on Windows; exposes directory listing of the entire drive |

---

## 5. External Process Interface (Agent Subprocess)

| ID | Interface | Direction | Input | Output | Notes |
|----|-----------|-----------|-------|--------|-------|
| EXT-001 | Agent CLI: `claude` / `claude-code` | Backend → External process | Prompt (task context JSON + instructions) via stdin or CLI arg | stdout/stderr, expected: JSON object with `action` field on last line | Executed via `subprocess.run`; working directory = workspace root; inherits backend environment |
| EXT-002 | Agent CLI: `codex` | Backend → External process | Same as above | Same as above | Command resolved via `ESAA_CODEX_COMMAND` env var or PATH |
| EXT-003 | Agent CLI: `gemini` / `gemini-cli` | Backend → External process | Same as above | Same as above | Command resolved via `ESAA_GEMINI_CLI_COMMAND` env var or PATH |

Agent output is parsed by `BaseAgentAdapter._extract_result_json`: scans output lines in reverse for a JSON dict with an `action` key. All agent output is untrusted until the manual decision gate.

---

## 6. Browser-to-API Interface (Summary)

| Input vector | Validated by | Trust level |
|---|---|---|
| Path parameters (`project_id`, `run_id`) | FastAPI routing (string match) | Untrusted |
| Query parameters (`path`, `roadmap`, `full`) | `_normalize_browse_path`, `_resolve_artifact_path` (path traversal guards) | Untrusted |
| JSON request bodies (`task_id`, `issue_id`, `decision`, etc.) | Pydantic schemas | Untrusted |
| Agent subprocess stdout/stderr | `_extract_result_json` (JSON parse + key check) + manual decision gate | Untrusted |

---

## 7. Entry Points Not Present (Confirmed Absent)

The following interfaces were checked and are **not present** in this workspace:

- WebSocket endpoints: none (SSE used instead of WebSocket)
- File upload endpoints: none (no `multipart/form-data` handlers, no `UploadFile` usage)
- GraphQL API: none
- gRPC / message queue consumers: none
- External HTTP callbacks / webhooks inbound: none
- Cloud provider SDK calls: none
- Database connections: none (filesystem-only storage)
- Authentication / session management layer: none (no auth middleware present)
- Reverse proxy (Nginx/Traefik): none declared in workspace

---

## 8. Attack Surface Summary

| Surface | Count | Highest-risk entries |
|---------|-------|----------------------|
| REST endpoints | 17 | EP-014 (file read), EP-031/032 (subprocess launch), EP-033 (event write + disk mutation), EP-011 (directory listing up to drive root) |
| SSE streams | 1 | SSE-001 (unauthenticated log stream) |
| File system read/write surfaces | 6 | FS-001 (activity.jsonl append), FS-002 (roadmap write), FS-006 (drive-root browse) |
| External process interfaces | 3 | EXT-001/002/003 (agent subprocess execution) |
| Authentication controls | 0 | Entire API surface is unauthenticated |
| Upload interfaces | 0 | — |
| WebSocket interfaces | 0 | — |

**Critical observation**: The entire API surface is unauthenticated and CORS is fully open (`*`). Any browser tab or local network client can invoke state-mutating endpoints including agent subprocess launch (EP-031, EP-032) and canonical event store writes (EP-033, EP-040, EP-050). This is declared as a known PoC limitation.
