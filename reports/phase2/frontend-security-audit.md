# Frontend Security Audit — SEC-024

**Playbook:** frontend_security (FE-001 a FE-004)
**Auditor:** codex
**Date:** 2026-03-08
**Scope:** `frontend/` React + TypeScript SPA
**Status:** COMPLETE

---

## Executive Summary

The audited frontend does not store authentication tokens in browser storage, does not use unsafe HTML rendering primitives, and does not implement business-critical enforcement logic on the client. The main residual gap is dependency vulnerability verification: `npm audit --json` could not complete in this restricted environment because the npm advisories endpoint was unreachable, so no current high/critical advisory baseline could be confirmed during this run.

| Check | Title | Status | Severity |
|-------|-------|--------|----------|
| FE-001 | Tokens armazenados em localStorage | PASS | LOW |
| FE-002 | HTML não sanitizado | PASS | LOW |
| FE-003 | Dependências JS vulneráveis | PARTIAL | MEDIUM |
| FE-004 | Lógica crítica no frontend | PASS | LOW |

**Overall frontend security posture:** ACCEPTABLE for the audited client-side patterns, with dependency advisory verification still required in a network-enabled CI or operator environment.

---

## FE-001 — Tokens armazenados em localStorage

**Status: PASS / LOW**

### Evidence

- `frontend/src/components/layout/AppShell.tsx:43-51` and `frontend/src/components/layout/AppShell.tsx:81-85` use `localStorage` only for the UI preference `esaa-sidebar-expanded`.
- `frontend/src/pages/ProjectLayout.tsx:7-28` uses `sessionStorage` only for the selected roadmap id (`esaa:selected-roadmap:<projectId>`).
- Repository-wide search over `frontend/src` found no auth token persistence patterns such as `localStorage.setItem(...token...)`, JWT storage, `document.cookie`, `Authorization` header construction, or login/session handling code.
- `frontend/src/services/api.ts:3-6` creates a plain Axios client with `baseURL` and `timeout`; no token injection or cookie manipulation is configured in the frontend client.

### Assessment

No authentication/session token storage was found in browser storage. The only persisted values are non-sensitive UX state.

---

## FE-002 — HTML não sanitizado

**Status: PASS / LOW**

### Evidence

- Repository-wide search found no use of `dangerouslySetInnerHTML`, raw `innerHTML`, `v-html`, or equivalent unsafe HTML rendering primitives in `frontend/src`.
- Dynamic rich content is rendered through `ReactMarkdown` in:
  - `frontend/src/pages/ChatPage.tsx:369-370`
  - `frontend/src/components/artifacts/ArtifactDetailDrawer.tsx:49-52`
- The implementation imports only `remark-gfm`; no `rehypeRaw` plugin or DOM sink was found that would re-enable raw HTML execution from Markdown input.

### Assessment

The current rendering path is materially safer than raw HTML injection. Based on the audited code, Markdown content is rendered through React component output rather than unsanitized DOM insertion.

---

## FE-003 — Dependências JS vulneráveis

**Status: PARTIAL / MEDIUM**

### Evidence

- Frontend dependencies are limited and pinned through `frontend/package-lock.json` with package integrity hashes.
- `frontend/index.html:10` loads only the local Vite entrypoint. No third-party CDN script tags were found, so there is no missing SRI finding in the audited HTML.
- `npm audit --json` was executed in `frontend/` and failed because the npm advisories endpoint could not be reached from this environment:

```text
request to https://registry.npmjs.org/-/npm/v1/security/advisories/bulk failed
```

- `npx tsc --noEmit` completed successfully, which validates TypeScript compilation but does not substitute for vulnerability intelligence.

### Assessment

No vulnerable dependency could be confirmed from static inspection alone, but current high/critical advisories also could not be ruled out during this run. This is an evidence gap, not proof of compromise.

### Recommendation

- Run `npm audit --json` in a CI or operator environment with registry access.
- Keep `package-lock.json` committed and add automated dependency scanning in CI.

---

## FE-004 — Lógica crítica no frontend

**Status: PASS / LOW**

### Evidence

- The main client-side calculations found are presentation/telemetry summaries such as token usage aggregation in `frontend/src/pages/RunsPage.tsx:19-75` and activity summaries in `frontend/src/components/activity/ActivityTimeline.tsx:23-76`.
- Task eligibility and execution gating are driven by backend-provided state fields (`is_eligible`, `ineligibility_reasons`, `remaining_run_slots`, `awaiting_decision`) defined in `frontend/src/services/projects.ts:34-151`.
- UI components such as `frontend/src/components/tasks/TasksDataGrid.tsx:41-71` use those fields only to enable/disable buttons and show operator hints. Actual state transitions still go through backend API calls in:
  - `frontend/src/services/runs.ts:42-86`
  - `frontend/src/services/projects.ts:181-239`

### Assessment

The audited frontend behaves as a control surface over server APIs, not as the source of truth for business-rule enforcement. No pricing, coupon, purchase, quota, or eligibility enforcement logic unique to the client was found.

---

## Verification Performed

- Static search for storage, token, auth, and cookie patterns across `frontend/src`
- Static search for unsafe HTML sinks (`dangerouslySetInnerHTML`, `innerHTML`, equivalents)
- Static inspection of Markdown rendering components
- Static inspection of run/task orchestration UI flows
- `npm audit --json` attempt in `frontend/` (blocked by unreachable npm advisories endpoint)
- `npx tsc --noEmit` in `frontend/` (passed)

---

## Summary of Findings

| ID | Check | Status | Severity | Evidence |
|----|-------|--------|----------|----------|
| FE-001 | Tokens em storage | PASS | LOW | Only UI preference and roadmap selection persisted |
| FE-002 | HTML não sanitizado | PASS | LOW | No raw HTML sinks; Markdown rendered without raw HTML plugin |
| FE-003 | Dependências JS vulneráveis | PARTIAL | MEDIUM | `npm audit` could not reach advisories endpoint; no CDN/SRI issue found |
| FE-004 | Lógica crítica no frontend | PASS | LOW | UI uses backend-derived state and API calls; no client-only enforcement found |

**Conclusion:** The frontend code audited in this run shows no direct evidence of token storage misuse, unsafe HTML injection, or business-critical client-side enforcement. Dependency advisory verification remains incomplete due environment network restrictions.
