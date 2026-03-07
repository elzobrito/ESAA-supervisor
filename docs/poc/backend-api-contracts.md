# ESUP-SPEC-002: Contratos de API Backend (FastAPI)

## 1. Visão Geral
O backend do Supervisor ESAA Web utiliza FastAPI para expor o estado do projeto e coordenar as runs. A comunicação é feita via HTTP JSON e streaming de logs via Server-Sent Events (SSE).

## 2. Base URL
A API deve ser acessada via `/api/v1`.

## 3. Recursos e Endpoints

### 3.1. Projetos (`/projects`)
- `GET /projects`: Lista todos os projetos disponíveis no diretório configurado.
  - **Response:** `200 OK` com `List[ProjectMetadata]`.
- `GET /projects/{project_id}`: Detalhes do projeto aberto.
  - **Response:** `200 OK` com `ProjectMetadata`.

### 3.2. Estado e Artefatos (`/projects/{project_id}/state`)
- `GET /projects/{project_id}/state`: Retorna o estado consolidado (Consolidated State).
  - **Response:** `200 OK` com `ConsolidatedState` (Roadmap, Issues, Lessons, Meta).
- `GET /projects/{project_id}/activity`: Lista os eventos de atividade.
  - **Response:** `200 OK` com `List[ActivityEvent]`.
- `GET /projects/{project_id}/artifacts`: Lista artefatos canônicos descobertos e sua integridade.
  - **Response:** `200 OK` com `List[CanonicalArtifact]`.

### 3.3. Tarefas (`/projects/{project_id}/tasks`)
- `GET /projects/{project_id}/tasks`: Lista todas as tarefas do roadmap.
  - **Response:** `200 OK` com `List[Task]`.
- `GET /projects/{project_id}/tasks/{task_id}`: Detalhes de uma tarefa específica.
  - **Response:** `200 OK` com `Task`.
- `GET /projects/{project_id}/tasks/eligible`: Retorna a lista de tarefas elegíveis no momento.
  - **Response:** `200 OK` com `List[Task]`.

### 3.4. Execuções (Runs) (`/projects/{project_id}/runs`)
- `POST /projects/{project_id}/runs/next`: Inicia a execução da próxima tarefa elegível.
  - **Response:** `201 Created` com `RunState`.
- `POST /projects/{project_id}/tasks/{task_id}/run`: Inicia a execução de uma tarefa específica.
  - **Response:** `201 Created` com `RunState`.
- `GET /projects/{project_id}/runs/current`: Status da run ativa (se houver).
  - **Response:** `200 OK` com `RunState` ou `404 Not Found`.
- `GET /projects/{project_id}/runs/{run_id}`: Status de uma run específica.
  - **Response:** `200 OK` com `RunState`.
- `POST /projects/{project_id}/runs/{run_id}/cancel`: Cancela uma run em andamento.
  - **Response:** `202 Accepted`.

### 3.5. Logs e Eventos em Tempo Real (`/projects/{project_id}/logs`)
- `GET /projects/{project_id}/logs/stream`: Streaming de logs da run ativa.
  - **Protocolo:** Server-Sent Events (SSE).
  - **Eventos:** `log`, `status_change`, `run_end`.

## 4. Esquemas de Dados Principais (Request/Response)

### 4.1. RunState
```json
{
  "run_id": "string",
  "task_id": "string",
  "agent_id": "string",
  "status": "preflight | running | syncing | cancelling | done | error",
  "started_at": "ISO-8601",
  "ended_at": "ISO-8601 | null",
  "exit_code": "int | null",
  "error_message": "string | null"
}
```

### 4.2. ConsolidatedState
```json
{
  "project_name": "string",
  "roadmap": { ... },
  "issues": { ... },
  "lessons": { ... },
  "last_event_seq": "int",
  "is_consistent": "boolean"
}
```

## 5. Códigos de Erro Específicos
- `409 Conflict`: Tentativa de iniciar uma run enquanto outra está ativa.
- `422 Unprocessable Entity`: Tentativa de rodar uma tarefa inelegível (dependências não cumpridas).
- `503 Service Unavailable`: Agente externo (Codex/Gemini/Claude) não configurado ou inacessível.
