# SEC-002 Architecture Map

## Scope and evidence

This document maps the architecture implemented in the current PoC workspace. It is based on the real code in `backend/app/`, `frontend/src/`, `.roadmap/`, and `scripts/run_poc_smoke.sh`.

## System context

The project is a local ESAA supervisor with four primary zones:

1. Browser client running the React/Vite dashboard.
2. FastAPI backend exposing project, state, run, task, issue, integrity, and log APIs.
3. Canonical ESAA artifact store under `.roadmap/`.
4. External agent CLIs and local process execution invoked by the backend run engine.

## Main components

### Frontend

- `frontend/src/router.tsx`
  Defines the route tree: project selection plus project-scoped pages for overview, tasks, runs, activity, artifacts, integrity, issues, and lessons.
- `frontend/src/pages/ProjectLayout.tsx`
  Loads consolidated project state from the backend and provides it through `ProjectContext`.
- `frontend/src/services/projects.ts`
  Calls project, state, artifact-content, file-browse, task-reset, issue-resolve, and integrity-repair endpoints.
- `frontend/src/services/runs.ts`
  Starts runs, polls run status, submits manual decisions, and cancels runs.
- `frontend/src/components/`
  Renders task tables, activity timelines, issue and lesson views, artifact readers, and run surfaces.

### Backend API

- `backend/app/main.py`
  Bootstraps FastAPI, enables permissive CORS for local PoC use, and mounts routers under `/api/v1`.
- `backend/app/api/routes_projects.py`
  Discovers projects, opens active projects, browses project files, and reads artifact content.
- `backend/app/api/routes_state.py`
  Aggregates roadmap variants, issues, lessons, artifacts, and activity into a consolidated UI state.
- `backend/app/api/routes_runs.py`
  Evaluates task eligibility, starts runs, resumes explicit tasks in `in_progress`, and applies manual decisions.
- `backend/app/api/routes_logs.py`
  Streams run logs over SSE.
- `backend/app/api/routes_tasks.py`, `routes_issues.py`, `routes_integrity.py`
  Support task reset, issue resolution, and integrity repair workflows.

### Core backend services

- `backend/app/core/canonical_store.py`
  Loads projection files and recent activity from `.roadmap/` and performs artifact discovery.
- `backend/app/core/artifact_discovery.py`
  Classifies `.roadmap/` files into roadmap, activity, issues, lessons, schema, policy, profile, and snapshot artifacts.
- `backend/app/core/selector.py` and `backend/app/core/eligibility.py`
  Determine next eligible tasks and validate whether a specific task may run.
- `backend/app/core/run_engine.py`
  Orchestrates supervised execution: preflight, optional claim, adapter invocation, manual decision, event persistence, and projection sync.
- `backend/app/core/event_writer.py`
  Appends canonical events to `activity.jsonl` with monotonic `event_seq` and `event_id`.
- `backend/app/core/projector.py`
  Applies claim/complete/review and mutation events to roadmap, issues, and lessons projections, then recomputes indexes and projection hash.
- `backend/app/core/log_stream.py`
  Maintains in-memory run logs and fan-out queues for SSE consumers.
- `backend/app/core/locks.py`
  Enforces a per-project logical lock during active runs.

### Agent integration layer

- `backend/app/core/agent_router.py`
  Chooses the adapter set for `codex`, `claude-code`, and `gemini-cli`.
- `backend/app/adapters/base.py`
  Runs external commands, captures stdout/stderr, extracts final JSON action, and normalizes failures to `issue.report`.
- `backend/app/adapters/*.py`
  Provide CLI-specific command building and prompt transport.

### Canonical data store

- `.roadmap/activity.jsonl`
  Append-only event source of truth.
- `.roadmap/roadmap.json` plus variant roadmaps such as `.roadmap/roadmap.security.json`
  Materialized task projections.
- `.roadmap/issues.json`
  Materialized issue projection.
- `.roadmap/lessons.json`
  Materialized lesson projection.
- `.roadmap/PROJECTION_SPEC.md`, `.roadmap/RUNTIME_POLICY.yaml`, `.roadmap/roadmap.schema.json`
  Operational and structural contracts.

## Integration points

### UI to backend

- HTTP JSON endpoints under `/api/v1/projects/*`.
- SSE endpoint under `/api/v1/projects/{project_id}/logs/stream/{run_id}`.

### Backend to filesystem

- Reads and writes `.roadmap/activity.jsonl`, `.roadmap/roadmap*.json`, `.roadmap/issues.json`, and `.roadmap/lessons.json`.
- Reads files from the project root and `.roadmap/` root when serving artifact content.
- Uses the workspace root as subprocess working directory for agent execution.

### Backend to external processes

- Invokes agent CLIs through `subprocess.run(...)`.
- Invokes the local backend process in smoke testing through `scripts/run_poc_smoke.sh`.

## Trust boundaries

### Boundary A: Browser to FastAPI

- Trust level: untrusted client to application server.
- Risk surface: all API and SSE requests can carry malformed input or trigger state-changing actions.
- Current controls: FastAPI routing, typed request/response schemas, project path normalization in project browsing APIs.
- Current weakness: `allow_origins=["*"]` in `backend/app/main.py` is explicitly permissive for the PoC.

### Boundary B: FastAPI to project filesystem

- Trust level: backend is trusted application code; project files are semi-trusted data.
- Risk surface: path traversal, artifact over-read, malformed JSON/JSONL, inconsistent projections.
- Current controls: path normalization and relative-path checks in `routes_projects.py`; consistency checks in `canonical_store.py`; projection hashing in roadmap metadata.
- Important observation: artifact reads intentionally permit both project-root and `.roadmap`-root resolution.

### Boundary C: FastAPI to `.roadmap` event store

- Trust level: append-only event store is the canonical source of truth but can still be corrupted by bad writers.
- Risk surface: concurrent appends, non-monotonic sequences, invalid status transitions, projection drift.
- Current controls: `EventWriter`, `Projector`, project lock, verify policy, and lessons explicitly forbidding parallel writers.
- Important observation: the current `EventWriter.next_event_seq()` reads the file to compute the next sequence, so serialization remains operationally critical.

### Boundary D: FastAPI to external agent CLIs

- Trust level: agent output is untrusted until parsed and manually approved.
- Risk surface: command execution failure, malformed JSON, unexpected file edits, oversized prompts, hostile or incorrect agent proposals.
- Current controls: adapter normalization to `issue.report`, explicit action whitelist, manual decision gate in `RunEngine`, and task-context scoping.

### Boundary E: Backend memory to log consumers

- Trust level: in-memory run logs are transient and trusted only while the process lives.
- Risk surface: log leakage to any SSE consumer with project/run identifiers.
- Current controls: route scoping by `project_id` and `run_id`.
- Current weakness: no authentication or authorization layer is present in the PoC.

## Runtime architecture narrative

1. The browser opens a project and requests consolidated state.
2. The backend loads `.roadmap` projections and recent activity through `CanonicalStore`.
3. The frontend renders task, issue, lesson, artifact, and integrity views from the aggregated response.
4. When the operator starts a run, the backend checks eligibility against the selected roadmap and open issues.
5. If the task is still `todo`, `RunEngine` records `claim` before invoking an agent.
6. The adapter executes the selected agent CLI and extracts one final JSON action proposal.
7. The run pauses for manual approval; the operator may apply or reject the proposed action.
8. On apply, the backend persists canonical events and reprojects roadmap/issues/lessons to disk.
9. The frontend refreshes state and optionally streams run logs through SSE.

## Architectural constraints relevant to SEC-002

- The source of truth is event-driven, not the roadmap projection alone.
- Roadmap variants can coexist in `.roadmap/`; the UI can operate on a selected roadmap or aggregate view.
- The system is local-first and process-driven rather than service-mesh or queue-driven.
- Manual review is a required control point between agent proposal and state mutation.

## Observed gaps

- `PARCER_PROFILE.agent-docs.yaml` was referenced by the execution instructions but is absent from `.roadmap/`.
- `docker-compose.yml`, `k8s/`, `terraform/`, and `docs/architecture.md` are not present; the implemented architecture is currently monorepo-local rather than container/orchestrator-based.
- The backend exposes permissive CORS and no authentication, which keeps trust boundaries thin for the PoC.
