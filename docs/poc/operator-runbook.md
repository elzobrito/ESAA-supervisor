# ESAA Supervisor PoC — Runbook Operacional

**Versão:** 1.0
**Data:** 2026-03-07
**Ambiente alvo:** Windows 11 / Linux / macOS (local, single-user)

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Clonar e configurar](#2-clonar-e-configurar)
3. [Subir o backend](#3-subir-o-backend)
4. [Subir o frontend](#4-subir-o-frontend)
5. [Verificar integridade do event store](#5-verificar-integridade-do-event-store)
6. [Executar a suite de testes](#6-executar-a-suite-de-testes)
7. [Executar o smoke test](#7-executar-o-smoke-test)
8. [Configurar agentes](#8-configurar-agentes)
9. [Fluxo de operação assistida](#9-fluxo-de-operação-assistida)
10. [Procedimentos de fallback](#10-procedimentos-de-fallback)
11. [Monitoramento e logs](#11-monitoramento-e-logs)

---

## 1. Pré-requisitos

| Ferramenta | Versão mínima | Verificação |
|---|---|---|
| Python | 3.11 | `python --version` |
| pip | 23+ | `pip --version` |
| Node.js | 18 | `node --version` |
| npm | 9+ | `npm --version` |
| Git | 2.x | `git --version` |
| curl | qualquer | `curl --version` |

---

## 2. Clonar e configurar

```bash
git clone <repo-url> ESAA-supervisor
cd ESAA-supervisor

# Backend
cd backend
pip install -r requirements.txt
cd ..

# Frontend
cd frontend
npm install
cd ..
```

---

## 3. Subir o backend

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8099 --reload
```

O servidor estará disponível em `http://127.0.0.1:8099`.

**Verificação rápida:**
```bash
curl http://127.0.0.1:8099/
# Esperado: {"status":"running","message":"ESAA Supervisor PoC"}
```

**Porta em uso (Windows):**
```cmd
netstat -ano | findstr 8099
taskkill /PID <PID> /F
```

**Porta em uso (Linux/macOS):**
```bash
lsof -ti :8099 | xargs kill -9
```

---

## 4. Subir o frontend

```bash
cd frontend

# Desenvolvimento (hot-reload)
npm run dev
# Disponível em http://localhost:5173

# Produção (build estático)
npm run build
# Artefatos em frontend/dist/
```

O frontend consome a API em `http://127.0.0.1:8099` (configurável em `frontend/src/services/api.ts`).

---

## 5. Verificar integridade do event store

O event store é o arquivo `.roadmap/activity.jsonl`. Para verificar:

```bash
# Checar sequência monotônica (sem gaps)
python3 - << 'EOF'
import json
lines = open(".roadmap/activity.jsonl").readlines()
events = [json.loads(l) for l in lines if l.strip()]
seqs = [e["event_seq"] for e in events]
gaps = [seqs[i] for i in range(1, len(seqs)) if seqs[i] != seqs[i-1] + 1]
print(f"Total events: {len(events)}, Last seq: {seqs[-1]}")
print(f"Gaps: {gaps or 'none'}")
EOF

# Checar hash de projeção
python3 - << 'EOF'
import json
data = json.load(open(".roadmap/roadmap.json", encoding="utf-8"))
print("verify_status:", data.get("verify_status", "n/a"))
print("last_event_seq:", data.get("last_event_seq"))
print("indexes:", data.get("indexes"))
EOF
```

---

## 6. Executar a suite de testes

```bash
cd backend
python -m pytest tests/ -v
```

Resultado esperado: **31 passed, 0 failed** (2 DeprecationWarnings de upstream são aceitáveis).

Módulos testados:
- `test_artifact_discovery.py` — descoberta de artefatos canônicos
- `test_validators.py` — validação JSON/JSONL/YAML
- `test_selector.py` — motor de elegibilidade e seleção de tarefas
- `test_runs_api.py` — API de runs (lifecycle completo via mocks)

---

## 7. Executar o smoke test

```bash
cd <raiz do projeto>
bash scripts/run_poc_smoke.sh
```

Resultado esperado: `14 passed, 0 failed`.

O script:
1. Inicia o backend na porta 8099
2. Executa 8 passos de verificação (health → state → eligibility → rejection paths → 404s)
3. Encerra o backend ao final

**Nota:** O smoke testa os caminhos de rejeição (`/runs/next` e `/runs/task`) quando não há tarefas elegíveis. Isso é o comportamento correto para o estado atual do projeto.

---

## 8. Configurar agentes

### 8.1 Agente padrão (gemini-cli)

O campo `agent_id` nos requests de run aceita qualquer string. O `RunEngine` do PoC executa um stub — a integração real com Gemini-CLI está fora do escopo do PoC.

Para simular um agente:
```bash
# Iniciar um run para a próxima tarefa elegível
curl -X POST http://127.0.0.1:8099/api/v1/projects/poc-project/runs/next \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "gemini-cli"}'

# Iniciar um run para uma tarefa específica
curl -X POST http://127.0.0.1:8099/api/v1/projects/poc-project/runs/task \
  -H "Content-Type: application/json" \
  -d '{"task_id": "ESUP-QA-018", "agent_id": "gemini-cli"}'
```

### 8.2 Claude Code como agente

Claude Code pode ser configurado como agente ESAA seguindo o protocolo definido em `.roadmap/init.yaml`. O fluxo é:
1. Leia `init.yaml` para carregar as regras do protocolo
2. Leia `roadmap.json` para ver o estado atual
3. Selecione a próxima tarefa elegível (status=todo, dependências=done)
4. Emita `task.claim` em `activity.jsonl`
5. Execute a tarefa
6. Emita `output.complete` e `review.approve`
7. Atualize `roadmap.json`

### 8.3 Acompanhar logs em tempo real (SSE)

```javascript
// Via EventSource (browser/frontend)
const es = new EventSource(
  'http://127.0.0.1:8099/api/v1/projects/poc-project/runs/{run_id}/logs'
);
es.onmessage = (e) => console.log(e.data);
```

```bash
# Via curl
curl -N http://127.0.0.1:8099/api/v1/projects/poc-project/runs/{run_id}/logs
```

---

## 9. Fluxo de operação assistida

```
Operador                 API Backend              Event Store
   |                         |                        |
   |-- GET /projects/ ------>|                        |
   |<-- [project list] ------|                        |
   |                         |                        |
   |-- GET /state/ --------->|-- lê roadmap.json ---->|
   |<-- [tasks + eligible] --|<-- dados projetados ----|
   |                         |                        |
   |-- GET /eligibility ---->|-- EligibilityEngine --->|
   |<-- [eligible_count] ----|                        |
   |                         |                        |
   |-- POST /runs/next ------>|-- RunEngine.start() -->|
   |<-- {run_id, status} ----|                        |
   |                         |                        |
   |-- GET /runs/{id} ------->| (poll até done/error)  |
   |<-- {status: "done"} ----|                        |
   |                         |                        |
   |-- GET /state/ --------->| (refresh do dashboard) |
   |<-- [estado atualizado] -|                        |
```

---

## 10. Procedimentos de fallback

### 10.1 Backend não sobe (porta em uso)

```bash
# Identificar processo
netstat -ano | grep 8099     # Linux/macOS
netstat -ano | findstr 8099  # Windows

# Matar processo (substituir <PID>)
kill -9 <PID>                # Linux/macOS
taskkill /PID <PID> /F       # Windows (via cmd)
```

### 10.2 Frontend não conecta ao backend (CORS)

O backend tem CORS liberado para `*` no PoC. Se houver erro de CORS, verifique `backend/app/main.py` → `CORSMiddleware`.

### 10.3 `/state/` retorna 404 "Project not active"

O backend requer que `GET /projects/` seja chamado antes de `GET /state/`. Chame `/projects/` primeiro para ativar o projeto no `CanonicalStore`.

### 10.4 Event store corrompido (gap de sequência)

```bash
# Identificar o gap
python3 - << 'EOF'
import json
events = [json.loads(l) for l in open(".roadmap/activity.jsonl") if l.strip()]
for i in range(1, len(events)):
    if events[i]["event_seq"] != events[i-1]["event_seq"] + 1:
        print(f"Gap entre {events[i-1]['event_id']} e {events[i]['event_id']}")
EOF
```

**Não edite `activity.jsonl` diretamente.** Abra ISS no roadmap e consulte o protocolo ESAA antes de qualquer ação corretiva.

### 10.5 `roadmap.json` divergiu do event store

Reprojetar manualmente a partir do event store. Consulte o Orchestrator ESAA ou abra uma issue de tipo `integrity`.

---

## 11. Monitoramento e logs

### Logs do backend

O uvicorn exibe logs no terminal. Para nível mais detalhado:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8099 --log-level debug
```

### Logs de runs

Cada run tem logs acessíveis via SSE em tempo real (durante execução) e via `GET /runs/{id}` após conclusão.

### Event store

```bash
# Últimos 5 eventos
tail -5 .roadmap/activity.jsonl | python3 -c "
import sys, json
for line in sys.stdin:
    e = json.loads(line)
    print(f\"{e['event_id']} | {e['ts']} | {e['actor']} | {e['action']} | task={e.get('task_id','—')}\")
"
```

---

*Runbook gerado por claude-code como parte de ESUP-QA-018.*
