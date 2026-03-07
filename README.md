# ESAA Supervisor

Local web supervisor for ESAA projects, built with FastAPI on the backend, React/Vite on the frontend, and filesystem-backed canonical state.

The application is designed to operate auditable roadmaps through the ESAA flow `claim -> complete -> review`, orchestrate agent executions (`codex`, `claude-code`, `gemini-cli`), and expose tasks, activity, artifacts, issues, lessons, and integrity checks through a single UI.

## Highlights

- open ESAA projects directly from the local filesystem
- detect multiple `roadmap*.json` files and switch between a single roadmap or an aggregated view
- run tasks with explicit agent selection and manual approval of the proposed action
- keep active runs alive while navigating inside the same project
- inspect logs, decision history, generated artifacts, and activity events
- browse project directories and read generated files from the UI
- render Markdown artifacts in formatted mode and code/text files in expanded viewers
- resolve issues, reset tasks to `todo`, and repair roadmap integrity from the interface

## Tech Stack

### Backend

- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic v2
- PyYAML
- `sse-starlette`

### Frontend

- React 18
- TypeScript
- Vite
- React Router
- Axios
- `react-markdown`
- `remark-gfm`

### Canonical State

- `.roadmap/roadmap.json`
- `.roadmap/roadmap.*.json`
- `.roadmap/activity.jsonl`
- `.roadmap/issues.json`
- `.roadmap/lessons.json`
- `.roadmap/init.yaml`

## Repository Layout

```text
backend/           API, execution runtime, adapters, projection logic
frontend/          React dashboard
.roadmap/          canonical artifacts and projections
docs/poc/          main PoC documentation
docs/ui-redesign/  UI redesign specs and QA artifacts
reports/           generated outputs from executed tasks
start-esaa-supervisor.bat
```

## Current Feature Set

### Project Operations

- project picker with directory browser
- active project switching
- multi-roadmap selection in the top bar
- aggregate roadmap mode for cross-roadmap task visibility

### Task and Run Supervision

- task grid with filters and detail drawer
- manual task execution for a selected task or the next eligible task
- agent chooser based on real CLI availability detected by the backend
- manual decision step for `claim`, `complete`, or `issue.report`
- persistent run session inside the current project
- live console dock with auto-scroll and elapsed time since the last response

### Audit and Artifact Surfaces

- activity timeline with payload inspection
- artifact catalog with preview and expanded reading mode
- project file browser for folders such as `reports/`
- issue panel with resolve action
- lessons panel
- integrity panel with repair action

## Requirements

- Python 3.10+
- Node.js 18+
- npm
- at least one authenticated agent CLI installed locally:
  - `codex`
  - `claude`
  - `gemini`

## Quick Start

### Windows Launcher

Use the root launcher:

```bat
start-esaa-supervisor.bat
```

It creates `.env` files from `.env.example` when missing and starts backend and frontend in separate windows.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Backend API: `http://127.0.0.1:8000`

### Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend UI: `http://localhost:3000`

## Usage

1. Open `http://localhost:3000/projects`.
2. Select a project from the directory browser.
3. Choose the active roadmap in the top bar.
4. Go to `Runs` to:
   - choose an agent
   - choose a task
   - run the next eligible task or a specific task
   - review the agent proposal
   - apply `claim`, `complete`, or `issue.report`
5. Use the remaining sections to inspect the project:
   - `Tasks`
   - `Activity`
   - `Artifacts`
   - `Issues`
   - `Lessons`
   - `Integrity`

## Agent Execution Notes

The adapters are tuned for local supervised execution:

- `codex`: `exec`, `workspace-write`, prompt via `stdin`
- `claude-code`: headless mode with `--permission-mode bypassPermissions`
- `gemini-cli`: headless mode with `--approval-mode yolo`

The backend exposes actual agent availability, and the UI disables unavailable agents accordingly.

## Validation

### Backend

```bash
cd backend
python -m compileall app
python -m pytest tests -q
```

### Frontend

```bash
cd frontend
npm run build
```

## Documentation

### Main PoC

- [Acceptance Checklist](docs/poc/acceptance-checklist.md)
- [Operator Runbook](docs/poc/operator-runbook.md)
- [Known Limitations](docs/poc/known-limitations.md)
- [E2E Smoke Report](docs/poc/e2e-smoke-report.md)
- [Final Report](docs/poc/final-report.md)

### UI Redesign

- [Usability Checklist](docs/ui-redesign/usability-checklist.md)
- [Heuristic Review Report](docs/ui-redesign/heuristic-review-report.md)
- [Visual Regression Report](docs/ui-redesign/visual-regression-report.md)
- [Final Acceptance Report](docs/ui-redesign/final-acceptance-report.md)

## Screenshots

Screenshots are not committed yet.

Recommended additions before publishing broadly:

- project picker
- tasks grid
- runs page with decision flow
- artifacts reader
- integrity and issues panels

## Roadmap

Short-term priorities:

- tighten the manual decision policy so invalid operator overrides are rejected
- improve multi-agent coordination around shared event stores
- add richer run history and resume workflows
- expand integrity diagnostics beyond roadmap hash mismatch

Medium-term directions:

- stronger event-store locking and reconciliation tooling
- more structured issue and lesson workflows
- broader QA automation around roadmap projections and agent execution
- packaging and deployment guidance beyond local PoC usage

## Known Limitations

- state is still fully filesystem-backed; there is no database layer
- concurrent writes to a shared `activity.jsonl` still require operational discipline
- the manual decision workflow exists, but its governance rules are still intentionally simple
- the system is optimized for local supervision, not multi-user production deployment

## Open Source Readiness

Before publishing publicly, it is still worth deciding:

- repository license
- contribution policy
- issue/PR templates
- whether `.roadmap` artifacts should ship as live examples or sanitized samples

## License

Choose and add the appropriate license before publishing the repository.
