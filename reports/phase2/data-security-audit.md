# Data Security Audit — SEC-023

**Playbook:** data_security (DA-001 a DA-005)
**Auditor:** claude-code
**Date:** 2026-03-08
**Scope:** ESAA Supervisor — full-stack (Python FastAPI backend + React/TypeScript frontend)
**Status:** COMPLETE

---

## Executive Summary

The ESAA Supervisor is an internal operator tool for orchestrating AI agents. It does **not** collect classical end-user PII (name, email, phone, CPF, etc.) and has no user registration or authentication layer. However, five significant data security gaps were identified:

| Check | Title | Status | Severity |
|-------|-------|--------|----------|
| DA-001 | PII Protection | PARTIAL | MEDIUM |
| DA-002 | Data Minimization | FAIL | MEDIUM |
| DA-003 | Retention Policy | FAIL | HIGH |
| DA-004 | Anonymization | PARTIAL | LOW |
| DA-005 | LGPD/GDPR Compliance | FAIL | HIGH |

---

## System Context

- **Storage:** JSON/JSONL files on local filesystem; no database, no cloud storage.
- **Users:** Internal operators only; no end-user accounts or user-facing PII fields.
- **Data processed:** Roadmap task data, AI agent outputs (stdout/stderr), chat session content, event audit trail.
- **Authentication:** None (PoC scope). Endpoints are unauthenticated.

---

## DA-001 — PII Protection

**Status: PARTIAL / MEDIUM**

### Findings

The system does not define PII data models (no user tables, no email/phone fields). However, two indirect PII exposure vectors exist:

1. **Chat message metadata stores raw process output** (`backend/app/core/chat_service.py:151–160`):
   ```python
   return {
       "content": response_extractor(stdout, stderr),
       "metadata": {
           "exit_code": completed.returncode,
           "stdout": stdout,       # full agent stdout
           "stderr": stderr,       # full agent stderr
           "command": command,     # command list with env-derived args
           "token_usage": ...
       },
   }
   ```
   Agent stdout/stderr may contain sensitive business data, filesystem paths, API keys encountered during agent execution, or other operator-injected content.

2. **Chat session title auto-derived from user message** (`backend/app/core/chat_store.py:87`):
   ```python
   session["title"] = content.strip().splitlines()[0][:72] or session["title"]
   ```
   The first 72 chars of any user chat message become the session title, which is exposed in session listings even to other sessions — potentially surfacing sensitive prompt content.

### Recommendation

- Scrub or truncate raw stdout/stderr before persisting to chat metadata.
- Do not derive session titles from message content, or redact before storage.

---

## DA-002 — Data Minimization

**Status: FAIL / MEDIUM**

### Findings

1. **Verbatim subprocess output persistence** (`chat_service.py:_run_subprocess`): Full `stdout`, `stderr`, and the raw `command` list are stored unconditionally in every chat message's `metadata` field and persisted to `chat_sessions/<uuid>.json`. There is no filtering, truncation, or need-based scoping.

2. **Activity event payloads** (`event_writer.py:build_event`): The `payload` field accepts and stores any dict without schema constraints. Agent results including full verification outputs and code diffs may be embedded verbatim.

3. **No size limits on chat content**: `ChatMessageCreateRequest.content` (schemas.py:249) has no `max_length` constraint. Arbitrarily large content (potentially including dumped files) can be persisted.

### Recommendation

- Define maximum lengths for stored fields (content, stdout/stderr).
- Limit stored subprocess output to meaningful excerpts (last N lines, or structured result only).
- Strip redundant raw output from persisted metadata after extraction.

---

## DA-003 — Retention Policy

**Status: FAIL / HIGH**

### Findings

No retention policy exists for any data category in the system:

| Data | Location | Retention | TTL/Cleanup |
|------|----------|-----------|-------------|
| Chat sessions | `.roadmap/chat_sessions/*.json` | Indefinite | Manual delete only |
| Activity log | `.roadmap/activity.jsonl` | Indefinite | Append-only, no rotation |
| Issues | `.roadmap/issues.json` | Indefinite | Manual close only |
| Lessons | `.roadmap/lessons.json` | Indefinite | Manual only |
| Roadmap | `.roadmap/roadmap.json` | Indefinite | Project lifecycle |

The `activity.jsonl` is append-only with no rotation, archival, or maximum size constraint. As agents run repeatedly, this file grows without bound, accumulating all agent outputs and task context indefinitely.

There is no `PRIVACY_NOTICE.md`, `RETENTION_POLICY.md`, or equivalent documentation.

### Recommendation

- Define and document a retention policy: e.g., chat sessions older than N days auto-deleted; activity.jsonl archived/rotated after M MB or N days.
- Implement a background cleanup job or operator-triggered purge command.
- Document the policy in the operator runbook.

---

## DA-004 — Anonymization / Pseudonymization

**Status: PARTIAL / LOW**

### Findings

1. **Positive**: Actor fields in `activity.jsonl` events use agent identifiers (`claude-code`, `gemini-cli`, `codex`) rather than personal operator identities. This provides implicit pseudonymization of operator actions.

2. **Gap**: Chat session messages associate content with `role: "user"` and `role: "assistant"` but do not link to any operator identity, which is acceptable in the current PoC scope (no authentication).

3. **Gap**: No anonymization mechanism exists for agent outputs before persistence. If an agent's output includes personal data encountered during file operations (e.g., scanning a directory with personal files), that data is stored verbatim.

4. **Gap**: No data scrubbing pipeline or regex-based PII detection before storage.

### Recommendation

- Add a lightweight PII scrubbing pass (e.g., redact email patterns, CPF patterns) before persisting agent stdout/stderr.
- Document the pseudonymization rationale in the privacy architecture.

---

## DA-005 — LGPD/GDPR Compliance

**Status: FAIL / HIGH**

### Findings

1. **No privacy notice** (`docs/` directory has no `privacy.md`, `lgpd.md`, or equivalent). LGPD Art. 9 requires transparent disclosure of data processing purposes.

2. **No consent mechanism**: The system provides no consent UI, no opt-in for data collection, no cookie banner. LGPD Art. 7–8 and GDPR Art. 6–7 require lawful basis for processing.

3. **No data subject rights implementation**: No endpoints or mechanisms for:
   - Right of access (Art. 18-I LGPD / Art. 15 GDPR)
   - Right to deletion (Art. 18-VI LGPD / Art. 17 GDPR)
   - Right to data portability (Art. 18-V LGPD / Art. 20 GDPR)

4. **No Data Processing Records (ROPA)**: No documented inventory of processing activities as required by LGPD Art. 37 / GDPR Art. 30.

5. **No DPO designation**: No Data Protection Officer identified or contact provided.

6. **CORS misconfiguration amplifies data exposure risk** (`main.py:28–34`):
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],   # all origins
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
   `allow_origins=["*"]` combined with `allow_credentials=True` is a contradictory configuration (browsers reject credentialed requests to wildcard origins per CORS spec) and signals no meaningful cross-origin access control — a precondition for data leakage via CSRF-style attacks.

7. **No encryption at rest**: Chat sessions and activity logs are stored as plaintext JSON/JSONL on the local filesystem without encryption. If the host is compromised, all data is immediately accessible.

### Applicability Note

As an internal PoC operator tool, LGPD/GDPR obligations are limited unless:
- Operators are identified natural persons whose actions are tracked.
- The tool processes documents containing end-user PII during agent-executed file operations.

Both conditions can occur in production use. The PoC label does not exempt the system from data protection obligations if deployed with real data.

### Recommendation

- Add `PRIVACY_NOTICE.md` documenting processing purposes, legal basis, and retention.
- Implement or document data subject rights handling procedure.
- Fix CORS: either restrict `allow_origins` to known origins or remove `allow_credentials=True`.
- Document ROPA for internal compliance.
- Evaluate encryption at rest for `chat_sessions/` if deployed with sensitive data.

---

## Cross-Cutting: Path Traversal Impact on Data Security

**Reference:** SEC-015 IV-007 (HIGH — already reported)

`chat_store.py:load_session` and `delete_session` use `session_id` as a filename without traversal sanitization. An attacker supplying `session_id = "../../roadmap/roadmap"` can read or delete canonical audit artifacts. This directly threatens data integrity and confidentiality in addition to the input validation finding.

---

## Summary of Findings

| ID | Check | Status | Severity | Evidence |
|----|-------|--------|----------|----------|
| DA-001 | PII Protection | PARTIAL | MEDIUM | stdout/stderr in metadata; session title from message |
| DA-002 | Data Minimization | FAIL | MEDIUM | Verbatim subprocess output persisted; no field size limits |
| DA-003 | Retention Policy | FAIL | HIGH | No retention for chat, activity.jsonl, issues, lessons |
| DA-004 | Anonymization | PARTIAL | LOW | Actors pseudonymized by agent-id; no content scrubbing |
| DA-005 | LGPD/GDPR Compliance | FAIL | HIGH | No privacy notice, no consent, no rights, CORS misconfiguration |

**Overall Data Security Posture: INSUFFICIENT for production with real data.**
