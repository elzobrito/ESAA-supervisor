# Auditoria de Segurança de API - SEC-014

## Resumo Executivo
A auditoria de segurança de API no sistema **ESAA-supervisor (PoC)** identificou falhas moderadas e graves em 5 dos 7 domínios avaliados. O sistema, embora utilize práticas modernas de definição de schema (Pydantic) e versionamento, carece de controles fundamentais de proteção contra abuso, como rate limiting, paginação e proteção contra replay attacks. A falha mais crítica de exposição de informação é a capacidade de navegar em qualquer diretório do host através do endpoint de browse de projetos.

## Detalhes dos Checks (Playbook AP-001 a AP-007)

| ID | Check | Status | Severidade | Evidência/Observação |
| --- | --- | --- | --- | --- |
| AP-001 | Endpoints sem rate limit | **FAIL** | HIGH | Ausência total de middleware ou decorators de limite de requisição em `main.py` e rotas. |
| AP-002 | Retorno de dados excessivos | **FAIL** | MEDIUM | Endpoint `/state` e `/chat/sessions/{id}` retornam estados completos e históricos integrais, sem filtragem ou carregamento parcial. |
| AP-003 | Enumeração de entidades | **FAIL** | MEDIUM | `/api/v1/projects/browse` permite enumerar diretórios e arquivos em todo o disco rígido do servidor. |
| AP-004 | Validação de schema | **PASS** | - | Uso consistente de Pydantic Models em todos os endpoints de entrada do FastAPI. |
| AP-005 | Versionamento de API | **PASS** | - | Implementação correta de prefixo `/api/v1` em todos os roteadores. |
| AP-006 | Ausência de paginação | **FAIL** | MEDIUM | Listas de atividades, tarefas, artefatos e sessões de chat não possuem suporte a `limit`/`offset`. |
| AP-007 | Replay attacks possíveis | **FAIL** | MEDIUM | Ações de mutação de estado e envio de mensagens não utilizam nonces ou chaves de idempotência. |

## Análise de Risco

### 1. Exposição de Sistema de Arquivos (AP-003)
O endpoint de navegação de projetos permite que um atacante remoto explore a estrutura de diretórios do servidor. Em sistemas Windows, o `BROWSE_ROOT` padrão é a raiz do drive (`C:\`), permitindo acesso visual a arquivos de sistema, logs e outros projetos fora do escopo do supervisor.

### 2. Abuso de Recursos e DoS (AP-001, AP-006)
A falta de rate limiting combinada com a ausência de paginação em payloads grandes (`StateResponse` com centenas de eventos) permite que um atacante sature a banda e a CPU do servidor com poucas requisições concorrentes.

### 3. Falta de Idempotência (AP-007)
A ausência de chaves de idempotência em endpoints de execução (`/runs/next`) e chat pode levar a execuções duplicadas de agentes LLM, causando desperdício financeiro (tokens) e inconsistência no estado do roadmap.

## Recomendações

1. **Implementar Rate Limiting**: Adicionar `slowapi` ao FastAPI para proteger todos os endpoints, com limites estritos para `/chat` e `/runs`.
2. **Isolar Browser de Projetos**: Restringir o acesso do `browse_projects` a um diretório de trabalho específico, impedindo a subida para diretórios pais do host.
3. **Paginação de Estado**: Refatorar o endpoint `/state` para retornar listas paginadas, especialmente para `activity` e `tasks`.
4. **Idempotency Keys**: Exigir o header `X-Idempotency-Key` para operações que alteram o estado do sistema ou disparam execuções de agentes.
5. **Filtragem de Payload**: Revisar as `ActivityEventResponse` para garantir que dados sensíveis não sejam vazados no campo `payload`.

---
Auditoria realizada por: gemini-cli
Data: 2026-03-07
Status da Task: complete
