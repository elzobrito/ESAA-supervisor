# Auditoria de Autorização - PARCER Security

## Sumário Executivo
A auditoria de autorização revelou um estado crítico de insegurança no sistema ESAA Supervisor. Como se trata de uma Prova de Conceito (PoC) focada em funcionalidade, a camada de segurança foi completamente omitida. Não existem mecanismos de autenticação, o que torna nula qualquer tentativa de autorização. Todos os endpoints operacionais, que permitem modificar o estado do projeto, resetar tarefas e executar agentes com permissões de escrita no sistema de arquivos, estão expostos publicamente.

## Resultados por Check (Playbook AZ)

| ID | Nome do Check | Status | Severidade | Evidência |
|:---|:---|:---:|:---:|:---|
| **AZ-001** | Controle de acesso ausente | **FAIL** | **CRITICAL** | Backend não possui middleware de auth. `APIRouter` em `routes_*.py` não define dependências de segurança. |
| **AZ-002** | IDOR (Insecure Direct Object Reference) | **FAIL** | **CRITICAL** | `routes_projects.py` permite navegar (`/browse`) e abrir (`/open`) qualquer diretório no drive do servidor que contenha um `.roadmap`. |
| **AZ-003** | Verificação de permissão apenas no frontend | **FAIL** | **CRITICAL** | Nenhuma lógica de permissão no backend. O frontend (`TaskDetailDrawer.tsx`) também expõe ações críticas sem checagem de role. |
| **AZ-004** | Admin routes expostas | **FAIL** | **HIGH** | Rotas de mutação de estado (`/tasks/reset`, `/tasks/review`) e controle de execução (`/runs/start`) são públicas. |
| **AZ-005** | Escopo de permissões mal definido | **FAIL** | **MEDIUM** | Não existe definição de Roles (ex: Admin, Operator, Auditor) no sistema. |
| **AZ-006** | Ações sensíveis sem confirmação | **FAIL** | **LOW** | Ações como "Regredir para todo" em `TaskDetailDrawer.tsx` e `review_task` na API não possuem step de confirmação. |

## Detalhamento Técnico

### 1. Ausência Total de Auth (AZ-001/AZ-003)
O sistema opera em modo "confiança total". Qualquer cliente que consiga alcançar a porta do backend pode disparar eventos de sistema, inclusive comandar agentes para realizar modificações no código-fonte através do endpoint de chat ou de runs.

### 2. IDOR e Navegação de Arquivos (AZ-002)
O endpoint `GET /projects/browse` utiliza uma raiz de navegação que, no Windows, pode ser o topo do drive (`C:\`). Embora haja uma validação para garantir que arquivos lidos estejam dentro do projeto aberto (`_resolve_artifact_path`), um atacante pode simplesmente "abrir" qualquer outro diretório do sistema como se fosse um projeto, desde que aponte para um caminho válido, burlando a segregação pretendida.

### 3. Exposição de APIs de Controle (AZ-004)
As rotas que gerenciam o ciclo de vida das tarefas (`claim`, `complete`, `review`) e das execuções (`runs`) não validam a identidade do ator. No código de `routes_tasks.py`, o `actor` é hardcoded como `"orchestrator"`, mascarando a origem real da requisição na trilha de auditoria (`activity.jsonl`).

## Recomendações de Remediação

### Curto Prazo (Imediato)
1. **Implementar Auth Middleware**: Adicionar uma camada de autenticação básica ou JWT para proteger todos os endpoints sob `/api/`.
2. **Step de Confirmação**: Adicionar diálogos de confirmação no frontend para ações destrutivas ou de mudança de estado crítica.

### Médio Prazo
1. **Definição de RBAC**: Implementar Roles (Admin, Operator, Viewer).
2. **Validar Actor Dinamicamente**: O campo `actor` nos eventos deve ser derivado da identidade autenticada, não fixo.
3. **Restringir Browser de Projetos**: Limitar o `BROWSE_ROOT` a um diretório específico de dados, impedindo a exploração de outros diretórios do servidor.

---
**Auditado por:** Gemini CLI (Agente ESAA)
**Data:** 2026-03-07
**Status Final:** REJEITADO (Falhas Críticas de Segurança)
