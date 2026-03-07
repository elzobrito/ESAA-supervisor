# ESAA Supervisor PoC — Checklist de Aceite

**Versão:** 1.0
**Data:** 2026-03-07
**Escopo:** PoC local single-user (esaa-supervisor-poc)

---

## Como usar

Marque cada item com ✅ (passou), ❌ (falhou) ou ⚠️ (parcial/observação).
A PoC é declarada **pronta para uso experimental** quando todos os itens críticos (🔴) estão ✅.

---

## 1. Pré-requisitos de Ambiente

| # | Criticidade | Item | Status |
|---|---|---|---|
| 1.1 | 🔴 | Python 3.11+ instalado (`python --version`) | ☐ |
| 1.2 | 🔴 | Dependências backend instaladas (`pip install -r backend/requirements.txt`) | ☐ |
| 1.3 | 🔴 | Node.js 18+ instalado (`node --version`) | ☐ |
| 1.4 | 🔴 | Dependências frontend instaladas (`cd frontend && npm install`) | ☐ |
| 1.5 | 🟡 | `curl` disponível no PATH | ☐ |
| 1.6 | 🟡 | Porta 8099 livre antes de iniciar o backend | ☐ |

---

## 2. Backend

| # | Criticidade | Item | Status |
|---|---|---|---|
| 2.1 | 🔴 | `GET /` retorna `{"status":"running"}` | ☐ |
| 2.2 | 🔴 | `GET /api/v1/projects/` retorna lista com `id` e `is_active:true` | ☐ |
| 2.3 | 🔴 | `GET /api/v1/projects/{id}/state/` retorna `tasks`, `is_consistent`, `eligible_task_ids` | ☐ |
| 2.4 | 🔴 | `GET /api/v1/projects/{id}/runs/eligibility` retorna `eligible_count` e `tasks` | ☐ |
| 2.5 | 🔴 | `POST /runs/next` retorna 422 quando não há tarefa elegível | ☐ |
| 2.6 | 🔴 | `POST /runs/task` com tarefa bloqueada retorna 422 com `message` | ☐ |
| 2.7 | 🔴 | `GET /runs/{bogus}` retorna 404 | ☐ |
| 2.8 | 🔴 | `DELETE /runs/{bogus}` retorna 404 | ☐ |
| 2.9 | 🟡 | Endpoint SSE `/runs/{id}/logs` responde com `text/event-stream` | ☐ |

---

## 3. Suite de Testes Automatizados

| # | Criticidade | Item | Status |
|---|---|---|---|
| 3.1 | 🔴 | `pytest backend/tests/` — todos os testes passam (31/31) | ☐ |
| 3.2 | 🔴 | Nenhum teste com `ERROR` ou `FAILED` | ☐ |
| 3.3 | 🟡 | Warnings aceitos: apenas DeprecationWarning de FastAPI (upstream) | ☐ |

---

## 4. Frontend

| # | Criticidade | Item | Status |
|---|---|---|---|
| 4.1 | 🔴 | `npm run build` termina com exit 0 | ☐ |
| 4.2 | 🔴 | Sem erros TypeScript (`tsc --noEmit`) | ☐ |
| 4.3 | 🟡 | `npm run dev` inicia sem erros de console | ☐ |
| 4.4 | 🟡 | Dashboard exibe lista de tarefas ao carregar | ☐ |
| 4.5 | 🟡 | Badge de status do run é exibido corretamente | ☐ |
| 4.6 | 🟡 | Painel de logs (RunConsole) exibe streaming ao iniciar um run | ☐ |

---

## 5. Integridade do Event Store

| # | Criticidade | Item | Status |
|---|---|---|---|
| 5.1 | 🔴 | `activity.jsonl` tem `event_seq` monotonicamente crescente (sem gaps) | ☐ |
| 5.2 | 🔴 | `roadmap.json` reflete o estado projetado do event store | ☐ |
| 5.3 | 🟡 | `verify_status` em `roadmap.json` não é `mismatch` | ☐ |
| 5.4 | 🟡 | Todas as tarefas completadas têm `completed_at` preenchido | ☐ |

---

## 6. Smoke Test Script

| # | Criticidade | Item | Status |
|---|---|---|---|
| 6.1 | 🔴 | `bash scripts/run_poc_smoke.sh` finaliza com exit 0 | ☐ |
| 6.2 | 🔴 | Output reporta "X passed, 0 failed" | ☐ |

---

## 7. Critérios de Pronta Entrega

A PoC é considerada **pronta para uso experimental** quando:

- [ ] Todos os itens 🔴 estão marcados ✅
- [ ] O smoke test passa com 0 falhas
- [ ] O relatório `docs/poc/e2e-smoke-report.md` está presente e atualizado
- [ ] Nenhum issue de severidade `critical` ou `high` está `open` sem mitigação documentada
- [ ] O runbook (`docs/poc/operator-runbook.md`) foi revisado por pelo menos um operador

---

## 8. Issues Abertas no Momento do Aceite

| Issue | Severidade | Título | Mitigação |
|---|---|---|---|
| ISS-0002 | 🔴 high | Concurrent writes quebram monotonicity | Operação single-writer; `ProjectLock` por projeto |

> ISS-0002 é conhecida e aceita para o escopo PoC (single-user local). Não bloqueia aceite experimental.

---

## Assinatura de Aceite

| Papel | Nome | Data | Assinatura |
|---|---|---|---|
| Responsável técnico | | | |
| Revisor de QA | | | |
