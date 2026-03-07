# SEC-001 - Inventario de Stack Tecnologica

## Escopo auditado

Workspace: `C:\xampp\htdocs\ESAA-supervisor`

Objetivo: mapear linguagens, frameworks, bancos de dados, servicos cloud e dependencias externas efetivamente evidenciados no repositorio.

## Resumo executivo

O sistema auditado e um monorepo local de PoC composto por:

- Core ESAA em Python empacotado via `pyproject.toml`
- Backend HTTP em Python com FastAPI
- Frontend SPA em TypeScript/React com Vite
- Armazenamento canonico baseado em arquivos JSON/JSONL na pasta `.roadmap`
- Integracao local com CLIs de agentes (`codex`, `claude`, `gemini`) via subprocesso

Nao ha evidencia de banco de dados dedicado, cache distribuido, mensageria, containerizacao ativa, orquestracao Kubernetes, IaC operacional ou SDKs de cloud provider no workspace inspecionado.

## Linguagens e runtimes

| Camada | Linguagem | Evidencia | Observacao |
| --- | --- | --- | --- |
| Core ESAA | Python 3.11+ | `pyproject.toml` (`requires-python = ">=3.11"`) | Biblioteca/orquestrador principal |
| Backend | Python | `backend/requirements.txt`, `backend/app/main.py` | API FastAPI |
| Frontend | TypeScript | `frontend/package.json`, `frontend/src/*.tsx`, `frontend/src/*.ts` | SPA React |
| Frontend | JavaScript runtime | `frontend/package.json` | Execucao por Node.js 18+ conforme `readme.md` |
| Shell operacional | Batch/PowerShell | `start-esaa-supervisor.bat`, instrucoes no `readme.md` | Suporte local de execucao |

## Frameworks e bibliotecas principais

### Core e backend Python

| Componente | Versao | Evidencia | Papel |
| --- | --- | --- | --- |
| FastAPI | `0.110.0` | `backend/requirements.txt` | API HTTP do supervisor |
| Uvicorn | `0.27.1` | `backend/requirements.txt` | ASGI server |
| Pydantic | `2.6.3` | `backend/requirements.txt` | Validacao e schemas |
| python-dotenv | `1.0.1` | `backend/requirements.txt` | Carregamento de ambiente |
| PyYAML | `6.0.1` | `backend/requirements.txt` | Leitura de artefatos YAML |
| sse-starlette | `2.0.0` | `backend/requirements.txt`, `backend/app/api/routes_logs.py` | Streaming SSE |
| jsonschema | `>=4.22.0` | `pyproject.toml` | Validacao estrutural do core ESAA |
| pytest | opcional `>=8.2.0` | `pyproject.toml` | Testes do core |

### Frontend

| Componente | Versao | Evidencia | Papel |
| --- | --- | --- | --- |
| React | `^18.2.0` | `frontend/package.json` | UI principal |
| React DOM | `^18.2.0` | `frontend/package.json` | Renderizacao no browser |
| React Router DOM | `^6.22.1` | `frontend/package.json` | Roteamento SPA |
| Axios | `^1.6.7` | `frontend/package.json`, `frontend/src/services/api.ts` | Cliente HTTP |
| Lucide React | `^0.344.0` | `frontend/package.json` | Iconografia |
| Vite | `^5.1.4` | `frontend/package.json`, `frontend/vite.config.ts` | Dev server e bundling |
| TypeScript | `^5.2.2` | `frontend/package.json` | Compilacao tipada |
| `@vitejs/plugin-react` | `^4.2.1` | `frontend/package.json` | Integracao React no Vite |

## Persistencia e armazenamento

| Tipo | Tecnologia | Evidencia | Conclusao |
| --- | --- | --- | --- |
| Estado canonico | Arquivos JSON/JSONL/YAML | `.roadmap/activity.jsonl`, `.roadmap/roadmap*.json`, `.roadmap/issues.json`, `.roadmap/lessons.json`, `.roadmap/init.yaml` | Fonte de verdade baseada em filesystem |
| Banco relacional | Nao evidenciado | Ausencia de `sqlalchemy`, `psycopg`, `sqlite`, `mysql`, `postgres` nos manifestos inspecionados | Nao declarado no workspace |
| Banco NoSQL | Nao evidenciado | Ausencia de `mongodb`, `redis` e SDKs relacionados | Nao declarado no workspace |

## Infraestrutura, rede e execucao

| Item | Evidencia | Observacao |
| --- | --- | --- |
| API local | `backend/.env.example` (`ESAA_HOST=127.0.0.1`, `ESAA_PORT=8000`) | Backend exposto localmente |
| Frontend local | `frontend/.env.example` (`VITE_API_BASE_URL=http://localhost:8000`) | Frontend aponta para backend local |
| Proxy dev | `frontend/vite.config.ts` | Proxy `/api` para `http://localhost:8000` |
| CORS aberto | `backend/app/main.py` | `allow_origins=["*"]` para PoC |
| SSE | `backend/app/api/routes_logs.py`, `frontend/src/services/logStream.ts` | Stream de logs em tempo real |
| Launcher local | `start-esaa-supervisor.bat` | Subida operacional simplificada |

Nao foram encontrados `Dockerfile`, `docker-compose.yml`, manifests Kubernetes ou Terraform na raiz do workspace auditado.

## Servicos cloud e terceiros

| Categoria | Tecnologia/Servico | Evidencia | Conclusao |
| --- | --- | --- | --- |
| Cloud provider | AWS/GCP/Azure | Nao ha SDKs, manifests ou variaveis de ambiente especificas | Nao evidenciado |
| LLM/agent CLI | `gemini`, `claude`, `codex` | `backend/app/adapters/*.py`, `backend/app/core/agent_router.py` | Integracao por subprocesso com CLIs locais |
| HTTP externo via frontend | Browser -> API local | `frontend/src/services/api.ts`, `frontend/src/services/logStream.ts` | Consumo principal da API do proprio sistema |
| Registro de pacotes | PyPI / npm | `backend/requirements.txt`, `frontend/package.json`, `frontend/package-lock.json` | Dependencias obtidas de ecossistemas publicos |

## Dependencias externas relevantes para auditoria

1. Dependencias Python gerenciadas por `pip` a partir de `backend/requirements.txt`.
2. Dependencias Node.js gerenciadas por `npm` a partir de `frontend/package.json` e `frontend/package-lock.json`.
3. Dependencia operacional de binarios locais dos agentes `gemini`, `claude` e `codex`, resolvidos por PATH ou variaveis `ESAA_<AGENT>_COMMAND`.
4. Dependencia de navegador com suporte a `EventSource` para streaming SSE no frontend.

## Ausencias relevantes

- Sem banco de dados declarado no repositorio.
- Sem Redis, fila, broker ou cache distribuido declarados.
- Sem cloud storage, object storage ou KMS evidenciados.
- Sem reverse proxy dedicado (Nginx/Traefik) declarado.
- Sem containerizacao declarada no workspace principal.

## Conclusao

O stack tecnologico atual e essencialmente local e orientado a arquivos: Python no core/backend, TypeScript/React no frontend, transporte HTTP/SSE e integracao com agentes por subprocesso. O principal vetor externo nao e um servico cloud, mas sim a cadeia de dependencias de pacotes e a disponibilidade dos CLIs de agentes configurados no ambiente.
