# ESAA Supervisor PoC — Relatório Final

**Projeto:** esaa-supervisor-poc
**Período:** 2026-02-27 → 2026-03-07
**Status:** ✅ Completo — 18/18 tarefas concluídas
**Agentes:** codex · gemini-cli · claude-code · orchestrator

---

## 1. Visão Geral

O **ESAA Supervisor PoC** é uma interface web local para gerenciar roadmaps seguindo o protocolo ESAA (claim → complete → review), com backend em **FastAPI** e frontend em **React/Vite**. O event store append-only em `activity.jsonl` é a fonte canônica de verdade; `roadmap.json`, `issues.json` e `lessons.json` são projeções materializadas.

```
.roadmap/activity.jsonl   ← event store (append-only, monotônico)
.roadmap/roadmap.json     ← projeção: estado das tarefas
.roadmap/issues.json      ← projeção: issues abertos/fechados
.roadmap/lessons.json     ← projeção: lições ativas
backend/                  ← FastAPI + RunEngine
frontend/                 ← React 18 + Vite + TypeScript
```

---

## 2. Roadmap — 18/18 Tarefas Concluídas

### Fase SPEC (4 tarefas)

| ID | Título | Agente |
|---|---|---|
| ESUP-SPEC-001 | Especificar pacote canônico, discovery de artefatos e resolução do roadmap ativo | codex |
| ESUP-SPEC-002 | Especificar runtime supervisor, ciclo de execução e contrato de runs | gemini-cli |
| ESUP-SPEC-003 | Especificar frontend React, modelo de tela e contratos visuais | gemini-cli |
| ESUP-SPEC-004 | Especificar adapters de agentes, roteamento e política de execução | gemini-cli |

### Fase IMPL (11 tarefas)

| ID | Título | Agente |
|---|---|---|
| ESUP-IMPL-005 | Scaffold do monorepo (FastAPI + React/Vite) | codex |
| ESUP-IMPL-006 | Registry de artefatos canônicos e discovery | gemini-cli |
| ESUP-IMPL-007 | Parse, validação estrutural e integridade de artefatos | gemini-cli |
| ESUP-IMPL-008 | Resolução do roadmap ativo, elegibilidade e seleção | gemini-cli |
| ESUP-IMPL-009 | Event writer append-only, projeção e sincronização | codex |
| ESUP-IMPL-010 | Runtime de runs em background com lock e cancelamento | gemini-cli |
| ESUP-IMPL-011 | Adapters para Codex, Claude Code e Gemini CLI | codex |
| ESUP-IMPL-012 | **API FastAPI completa + streaming de logs (SSE)** | **claude-code** |
| ESUP-IMPL-013 | Shell React, rotas, cliente HTTP e modelo base de estado | gemini-cli / codex |
| ESUP-IMPL-014 | Dashboard React (artefatos, tasks, activity, issues, lessons) | codex |
| ESUP-IMPL-015 | **Console de execução, ações de run e atualização em tempo real** | **claude-code** |

### Fase QA (3 tarefas)

| ID | Título | Agente |
|---|---|---|
| ESUP-QA-016 | **Suite de testes backend** (discovery, validação, seleção, runs API) | **claude-code** |
| ESUP-QA-017 | **Smoke test ponta a ponta** | **claude-code** |
| ESUP-QA-018 | **Checklist de aceite, runbook operacional e known-limitations** | **claude-code** |

---

## 3. Arquitetura

### 3.1 Backend — `backend/app/`

```
app/
├── main.py                     # FastAPI app, CORS, routers
├── api/
│   ├── schemas.py              # Pydantic models: StateResponse, RunResponse, EligibilityReportResponse...
│   ├── routes_projects.py      # GET /projects/, GET /projects/{id}
│   ├── routes_state.py         # GET /projects/{id}/state/
│   ├── routes_runs.py          # POST /runs/next, POST /runs/task, GET/DELETE /runs/{id}
│   └── routes_logs.py          # GET /runs/{id}/logs  (SSE)
├── core/
│   ├── artifact_discovery.py   # ArtifactDiscovery: varre .roadmap/, classifica artefatos
│   ├── canonical_store.py      # CanonicalStore: carrega roadmap, issues, lessons, activity
│   ├── eligibility.py          # EligibilityEngine: check_eligibility(task_id)
│   ├── selector.py             # TaskSelector: select_next_task(), get_task_status_report()
│   ├── event_writer.py         # EventWriter: append_event() monotônico
│   ├── projector.py            # Projector: replay do event store, compute_projection_hash()
│   ├── run_engine.py           # RunEngine: start_run(), cancel_run(), get_run_state()
│   ├── locks.py                # ProjectLock: mutex por projeto
│   ├── log_stream.py           # LogStreamer: SSE generator
│   ├── validators.py           # Validators: JSON, JSONL, YAML, JSON Schema
│   ├── agent_router.py         # AgentRouter: roteia task → adapter
│   ├── roadmap_resolution.py   # Resolução do roadmap ativo
│   └── schema_validation.py    # Validação contra JSON Schema
├── adapters/
│   ├── base.py                 # AgentAdapter (ABC)
│   ├── claude_adapter.py       # ClaudeAdapter
│   ├── gemini_adapter.py       # GeminiAdapter
│   └── codex_adapter.py        # CodexAdapter
├── models/
│   ├── canonical_artifact.py   # CanonicalArtifact, ArtifactCategory, ArtifactRole
│   ├── project_state.py        # ProjectState, RawProjectState
│   ├── run_state.py            # RunState, RunStatus
│   ├── task_context.py         # TaskContext
│   └── agent_result.py         # AgentResult
└── utils/
    └── jsonl.py                # read_jsonl(), write_jsonl()
```

**Endpoints implementados:**

| Método | Path | Descrição |
|---|---|---|
| GET | `/` | Health check |
| GET | `/api/v1/projects/` | Lista projetos |
| GET | `/api/v1/projects/{id}` | Detalhes do projeto |
| GET | `/api/v1/projects/{id}/state/` | Estado consolidado (tasks + issues + lessons + artifacts + activity) |
| GET | `/api/v1/projects/{id}/runs/eligibility` | Relatório de elegibilidade |
| POST | `/api/v1/projects/{id}/runs/next` | Inicia run para próxima tarefa elegível |
| POST | `/api/v1/projects/{id}/runs/task` | Inicia run para tarefa específica (com validação) |
| GET | `/api/v1/projects/{id}/runs/{run_id}` | Status do run |
| DELETE | `/api/v1/projects/{id}/runs/{run_id}` | Cancela run |
| GET | `/api/v1/projects/{id}/runs/{run_id}/logs` | Streaming de logs via SSE |

### 3.2 Frontend — `frontend/src/`

```
src/
├── App.tsx
├── router.tsx
├── main.tsx
├── pages/
│   ├── ProjectsPage.tsx         # Lista de projetos
│   └── ProjectDashboardPage.tsx # Dashboard principal com run lifecycle
├── components/
│   ├── TasksTable.tsx           # Tabela de tarefas com status e ação "Run"
│   ├── TaskDetails.tsx          # Detalhes da tarefa selecionada
│   ├── RunControls.tsx          # Botões: Run Next, Refresh, Cancel
│   ├── RunStatusBadge.tsx       # Badge colorido de status do run
│   ├── RunConsole.tsx           # Console de logs em tempo real (SSE)
│   ├── ActivityPanel.tsx        # Feed de eventos do event store
│   ├── ArtifactsPanel.tsx       # Lista de artefatos canônicos
│   ├── IssuesPanel.tsx          # Issues abertas
│   └── LessonsPanel.tsx         # Lições ativas
└── services/
    ├── api.ts                   # axios instance + extractErrorMessage
    ├── projects.ts              # fetchProjectState() → StateResponse
    ├── runs.ts                  # startNextRun, startTaskRun, fetchRunStatus, cancelRun
    └── logStream.ts             # subscribeToLogs() via EventSource (SSE)
```

---

## 4. Testes Automatizados

**Resultado: 31/31 passed, 0 failed**

```
backend/tests/
├── test_artifact_discovery.py   (6 testes)
├── test_canonical_store.py      (1 teste)
├── test_event_writer.py         (1 teste)
├── test_health.py               (1 teste)
├── test_projector.py            (1 teste)
├── test_run_engine.py           (1 teste)
├── test_runs_api.py             (6 testes)
├── test_selector.py             (7 testes)
└── test_validators.py           (7 testes)
```

### Detalhamento por módulo

#### `test_artifact_discovery.py` — 6 testes ✅
- Descobre projeções canônicas (roadmap.json, issues.json, lessons.json)
- Classifica plugins de roadmap
- Classifica PARCER profiles
- Classifica schemas JSON
- Classifica contratos YAML
- Retorna lista vazia para diretório inexistente

#### `test_canonical_store.py` — 1 teste ✅
- `is_consistent` segue o `verify_status` do roadmap

#### `test_event_writer.py` — 1 teste ✅
- Append de eventos usa sequência monotônica crescente (sem gaps)

#### `test_health.py` — 1 teste ✅
- `GET /` retorna `{"status": "running"}`

#### `test_projector.py` — 1 teste ✅
- Projector aplica claim → complete → review e resolução de issues corretamente

#### `test_run_engine.py` — 1 teste ✅
- Run cancelado não finaliza com `status: done`

#### `test_runs_api.py` — 6 testes ✅
- `GET /` retorna running
- `GET /eligibility` retorna tarefa elegível com `eligible_count`
- `POST /runs/next` retorna `run_id` e `status: preflight` (ciclo completo via mock)
- `POST /runs/next` retorna 422 quando não há tarefa elegível
- `DELETE /runs/{bogus}` retorna 404
- `GET /runs/{bogus}` retorna 404

#### `test_selector.py` — 7 testes ✅
- Seleciona primeira tarefa elegível (todo + deps done)
- Retorna `None` quando não há elegível
- Respeita dependências não resolvidas
- Tarefa se torna elegível após dependência completada
- `get_eligible_tasks()` retorna todas elegíveis
- Relatório inclui razões de inelegibilidade
- Issue crítica não bloqueia tarefas não relacionadas

#### `test_validators.py` — 7 testes ✅
- JSON válido passa / inválido falha
- JSONL válido passa / inválido falha
- YAML válido passa / inválido falha
- JSON Schema é aplicado quando presente

---

## 5. Smoke Test — `scripts/run_poc_smoke.sh`

**Resultado: 14/14 passed, 0 failed**

| # | Step | Verificação | Resultado |
|---|---|---|---|
| 1 | Health | `GET /` → `"status":"running"` | ✅ |
| 2 | Projects | `GET /projects/` → lista com `id` | ✅ |
| 2 | Projects | `is_active: true` | ✅ |
| 3 | State | `GET /state/` → `tasks` | ✅ |
| 3 | State | `GET /state/` → `is_consistent` | ✅ |
| 3 | State | `GET /state/` → `eligible_task_ids` | ✅ |
| 4 | Eligibility | `GET /eligibility` → `eligible_count` | ✅ |
| 4 | Eligibility | `GET /eligibility` → `tasks` | ✅ |
| 5 | Runs next | `POST /runs/next` → 422 (sem elegível) | ✅ |
| 5 | Runs next | Corpo contém `"detail"` | ✅ |
| 6 | Task bloqueada | `POST /runs/task` QA-018 → 422 | ✅ |
| 6 | Task bloqueada | Corpo contém `"message"` | ✅ |
| 7 | Run 404 | `GET /runs/{bogus}` → 404 | ✅ |
| 8 | Delete 404 | `DELETE /runs/{bogus}` → 404 | ✅ |

---

## 6. Build Frontend

```
npm run build → EXIT 0
dist/index.html           1.08 kB
dist/assets/index-*.css  ~12 kB
dist/assets/index-*.js   ~340 kB
```

Sem erros TypeScript. Sem warnings de lint.

---

## 7. Event Store

O event store registra **59 eventos** (EV-00000001 → EV-00000059) ao longo de todo o ciclo de vida do projeto.

| Período | Agente | Atividade |
|---|---|---|
| EV-01..09 | orchestrator | Inicialização do projeto, criação das primeiras tarefas, verify |
| EV-10..44 | codex, gemini-cli | SPEC-001..004, IMPL-005..014 |
| EV-45..47 | **claude-code** | IMPL-012: API FastAPI completa |
| EV-48..50 | **claude-code** | IMPL-015: console de execução React |
| EV-51..53 | **claude-code** | QA-016: suite de testes backend |
| EV-54..56 | **claude-code** | QA-017: smoke test ponta a ponta |
| EV-57..59 | **claude-code** | QA-018: checklist, runbook, known-limitations |

Protocolo respeitado em todos os eventos claude-code: `claim → output.complete → review.approve` com `prior_status` explícito em cada envelope.

---

## 8. Documentação Produzida

| Arquivo | Conteúdo |
|---|---|
| `docs/poc/e2e-smoke-report.md` | Relatório de smoke test com evidências, gaps e limitações |
| `docs/poc/acceptance-checklist.md` | 25 itens de aceite em 6 seções, critérios de pronta entrega |
| `docs/poc/operator-runbook.md` | Setup, agentes, SSE, fallbacks, monitoramento (11 seções) |
| `docs/poc/known-limitations.md` | 9 limitações, 8 débitos técnicos, próximos passos em 3 horizontes |
| `scripts/run_poc_smoke.sh` | Script bash de smoke test end-to-end (14 verificações) |
| `readme.md` | Atualizado com smoke, testes e tabela de links de docs |

---

## 9. Issues e Lições

### Issue aberta

| ID | Severidade | Título | Status |
|---|---|---|---|
| ISS-0002 | High | Concurrent writes to activity.jsonl break monotonicity | Open — mitigado por single-writer na PoC |

### Lições ativas (da sessão)

- **LES-0001** Nunca colapsar claim + complete + review em um único evento
- **LES-0002** Sempre verificar `prior_status` antes de emitir evento
- **LES-0003** Ler `roadmap.json` diretamente; MCP `esaa_get_state` não resolve caminhos Windows
- **LES-0004** FastAPI redireciona rotas sem trailing slash (307); sempre testar com `/state/`
- **LES-0005** Verificar elegibilidade real antes de identificar próxima tarefa (IMPL-010 estava `done`, não `todo`)

---

## 10. Limitações Conhecidas (resumo)

| # | Limitação |
|---|---|
| 1 | Single-project por instância (`CanonicalStore` singleton) |
| 2 | `RunEngine` executa stub — integração real com agentes não implementada |
| 3 | Sem autenticação nos endpoints |
| 4 | Escritas concorrentes no event store não são atômicas entre processos (ISS-0002) |
| 5 | `verify_status` não é recomputado automaticamente |
| 6 | SSE não testado end-to-end via smoke (apenas via mocks) |
| 7 | `ROADMAP_DIR` hardcoded — backend deve ser iniciado a partir de `backend/` |
| 8 | `fuser` não disponível no Windows (kill manual de porta necessário) |

Detalhes completos em [`docs/poc/known-limitations.md`](known-limitations.md).

---

## 11. Critérios de Pronta Entrega — Status Final

| Critério | Status |
|---|---|
| Todos os 18 tasks done | ✅ |
| Smoke test 0 falhas | ✅ 14/14 |
| Suite de testes 0 falhas | ✅ 31/31 |
| Frontend build limpo | ✅ exit 0 |
| Checklist de aceite presente | ✅ |
| Runbook operacional presente | ✅ |
| Limitações documentadas | ✅ |
| ISS-0002 mitigada para escopo PoC | ✅ |

**A PoC está pronta para uso experimental local.**

---

*Relatório gerado por claude-code em 2026-03-07.*
