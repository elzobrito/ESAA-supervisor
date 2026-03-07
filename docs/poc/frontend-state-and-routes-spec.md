# ESUP-SPEC-003: Especificação de Rotas e Estado do Frontend (React)

## 1. Modelo de Navegação (Rotas)
O frontend utiliza `react-router-dom` para gerenciar a navegação entre as visões da aplicação.

### 1.1. Principais Rotas
- `/`: Redireciona para a lista de projetos ou dashboard do projeto padrão.
- `/projects`: Lista todos os diretórios/projetos monitorados pelo supervisor.
- `/dashboard/:project_id`: Dashboard principal de um projeto específico.
- `/settings`: Configurações globais (API endpoints, preferências de UI).

## 2. Gerenciamento de Estado (Store)
O estado da aplicação é gerenciado em memória (React Context ou Store simplificada) para garantir reatividade e consistência.

### 2.1. Estado Global
- `projectsList`: Array de metadados dos projetos conhecidos.
- `activeProject`: Detalhes do projeto aberto (ID, nome, caminho).

### 2.2. Estado do Projeto (Project Store)
- `roadmap`: JSON das tarefas lido do `roadmap.json`.
- `activity`: Lista de eventos lidos de `activity.jsonl`.
- `issues`: Lista de problemas lida de `issues.json`.
- `lessons`: Lista de lições aprendida de `lessons.json`.
- `artifacts`: Catálogo de artefatos canônicos com metadados de integridade.

### 2.3. Estado de Execução (Run Store)
- `currentRun`: Objeto contendo o status da run ativa (`run_id`, `task_id`, `status`).
- `logs`: Buffer de strings recebidas via SSE.
- `isStreaming`: Boolean indicando se a conexão SSE está aberta.

## 3. Serviços de API (Axios/Fetch)
Camada de serviços para isolar as chamadas HTTP para o backend FastAPI.

### 3.1. Project Service
- `fetchProjects()`: `GET /projects`
- `fetchProjectState(projectId)`: `GET /projects/{id}/state`

### 3.2. Run Service
- `startNextRun(projectId)`: `POST /projects/{id}/runs/next`
- `startTaskRun(projectId, taskId)`: `POST /projects/{id}/tasks/{taskId}/run`
- `cancelRun(projectId, runId)`: `POST /projects/{id}/runs/{runId}/cancel`
- `subscribeToLogs(projectId)`: Inicia `EventSource` para o endpoint de logs.

## 4. Sincronização e Revalidação
- **Poll Inativo:** Quando nenhuma run está ativa, o frontend pode fazer polling leve (ex: a cada 30s) ou via WebSocket para detectar mudanças externas nos arquivos `.roadmap/`.
- **Refresh Pós-Run:** Ao receber o evento `run_end` via SSE, o frontend invalida o cache do `Project Store` e dispara um re-fetch imediato.

## 5. Mock de Desenvolvimento
O frontend deve suportar um modo de desenvolvimento com mocks para permitir o trabalho na interface sem depender de um backend FastAPI ativo.
