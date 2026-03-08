# Input Validation Audit — SEC-015
**Playbook:** input_validation (IV-001 a IV-007)
**Data:** 2026-03-07
**Auditor:** claude-code
**Task ID:** SEC-015
**Escopo:** Backend (Python/FastAPI) + Frontend (React/TypeScript)

---

## Sumário Executivo

O sistema ESAA Supervisor foi auditado para os vetores IV-001 a IV-007 do playbook de validação de entrada. O stack não usa banco de dados relacional, portanto SQL injection é inaplicável. Foram identificadas **2 vulnerabilidades de impacto imediato** (path traversal via `session_id` e prompt injection via chat), **3 gaps de configuração médios** (CORS wildcard, ausência de limite de payload, exposição de metadados internos) e **2 áreas sem exposição direta** (XSS, SSRF direto).

| # | Vetor | Status | Severidade |
|---|-------|--------|-----------|
| IV-001 | SQL Injection | N/A | — |
| IV-002 | Command Injection | PASS com ressalvas | LOW |
| IV-003 | Template / Prompt Injection | FAIL | MEDIUM |
| IV-004 | SSRF | N/A (risco indireto) | LOW |
| IV-005 | XSS | PASS | LOW |
| IV-006 | Inputs não validados | PARTIAL | MEDIUM |
| IV-007 | Sanitização ausente | FAIL | HIGH |

---

## IV-001 — SQL Injection

**Status: NÃO APLICÁVEL**

O sistema não utiliza banco de dados relacional. Toda a persistência ocorre via arquivos JSON/JSONL no diretório `.roadmap/`. Não há queries SQL, ORM ou driver de banco de dados no codebase.

---

## IV-002 — Command Injection

**Status: PASS com ressalvas — LOW**

### Análise

Dois locais invocam `subprocess.run()`:

- `backend/app/adapters/base.py:70` — execução dos agentes (codex, claude-code, gemini-cli)
- `backend/app/core/chat_service.py:137` — chat interativo com agentes

Ambos usam a forma de lista (`command=[...]`) sem `shell=True`, o que **previne shell injection** convencional via metacaracteres. Conteúdo do usuário é enviado via `stdin`, não via argumentos de linha de comando.

### Vetores Residuais

1. **`cwd=context.metadata.get("workspace_root")`** (`base.py:72`)
   O diretório de trabalho é extraído de `context.metadata`. Se um projeto mal-formado injetar um `workspace_root` arbitrário, o subprocess executará no diretório errado.

2. **`resolve_command()` via variável de ambiente** (`base.py:32`)
   Lê `ESAA_<ACTOR>_COMMAND` do ambiente. Se o ambiente for comprometido, o comando pode ser redirecionado para executável malicioso.

3. **Wrapping `.cmd/.bat` no Windows** (`base.py:129-130`)
   ```python
   if os.name == "nt" and executable.lower().endswith((".cmd", ".bat")):
       return ["cmd", "/c", executable, *command[1:]]
   ```
   Arquivos `.cmd`/`.bat` são wrappados com `cmd /c`. Se o caminho do executável for controlável via variável de ambiente, há vetor de execução arbitrária no Windows.

### Recomendação

- Validar `workspace_root` contra lista de projetos permitidos antes de passá-lo ao subprocess.
- Restringir variáveis `ESAA_*_COMMAND` a caminhos absolutos dentro de diretórios confiáveis.

---

## IV-003 — Template Injection / Prompt Injection

**Status: FAIL — MEDIUM**

### Análise

`backend/app/core/chat_service.py:_build_prompt()` interpola conteúdo do usuário diretamente na string de prompt enviada ao agente LLM:

```python
# chat_service.py:66
lines.append(f"USER: {user_message}")
```

O campo `user_message` é o conteúdo literal enviado pelo operador via `POST /projects/{id}/chat/sessions/{session_id}/messages`. Não há filtro, escape ou validação de padrões de injeção antes da interpolação.

Adicionalmente, contexto de task do roadmap também é interpolado sem sanitização:

```python
# chat_service.py:51-57
lines.append(f"- description: {task_context.get('description')}")
```

### Fator Agravante

Os agentes são executados com modos de aprovação automática de ferramentas:

```python
# claude_adapter.py:22
"--permission-mode", "bypassPermissions",

# gemini_adapter.py:24
"--approval-mode", "yolo",
```

Isso significa que um prompt injection bem-sucedido pode induzir o agente a executar ferramentas (leitura/escrita de arquivos, comandos de sistema) **sem qualquer confirmação**.

### Impacto

Um operador com acesso à API de chat pode injetar instruções de sistema no prompt, induzindo o agente a: modificar arquivos do projeto, vazar conteúdo sensível, executar comandos no contexto do workspace.

### Recomendação

- Delimitar conteúdo do usuário com marcadores estruturais (ex.: XML tags) reconhecidos como dados, não instruções.
- Avaliar se `bypassPermissions`/`yolo` são necessários para sessões de chat interativo (vs. automação de tasks).
- Adicionar system prompt de segurança instruindo o modelo a rejeitar tentativas de override de papel.

---

## IV-004 — SSRF (Server-Side Request Forgery)

**Status: NÃO APLICÁVEL como SSRF direto — LOW (risco indireto)**

### Análise

Nenhum endpoint aceita URLs fornecidas pelo usuário para realizar requisições HTTP do servidor. Os endpoints de browse e artifact validam caminhos contra raízes permitidas:

```python
# routes_projects.py:25
if os.path.commonpath([BROWSE_ROOT, target]) != BROWSE_ROOT:
    raise HTTPException(status_code=400, ...)

# routes_projects.py:74-78
if not (resolved.is_relative_to(project_root) or resolved.is_relative_to(roadmap_root)):
    raise HTTPException(status_code=400, ...)
```

### Risco Indireto

Os agentes LLM têm capacidade de fazer requisições HTTP (ferramentas de fetch/curl disponíveis). Um prompt injection bem-sucedido (IV-003) poderia induzir o agente a fazer SSRF internamente contra serviços locais.

---

## IV-005 — XSS (Cross-Site Scripting)

**Status: PASS — LOW**

### Análise

O frontend React usa JSX, que escapa automaticamente todo conteúdo inserido via `{variável}`. Varredura em `frontend/src/**/*.tsx` não encontrou:

- `dangerouslySetInnerHTML` — ausente
- `innerHTML` — ausente
- `eval()` — ausente
- `document.write` — ausente

O componente `ChatPage.tsx` renderiza respostas LLM via `<ReactMarkdown>` com `remarkGfm`. ReactMarkdown não renderiza HTML arbitrário por padrão (plugin `rehype-raw` não está em uso).

### Observação: CORS Wildcard

`main.py:28-34`:
```python
allow_origins=["*"],
allow_credentials=True,
```

A combinação `allow_origins=["*"]` com `allow_credentials=True` é tecnicamente rejeitada por browsers (CORS spec §3.2.2), mas é uma má prática. Recomenda-se restringir origins à origem real do frontend em produção.

---

## IV-006 — Inputs Não Validados

**Status: PARTIAL — MEDIUM**

### Achados

#### 1. Ausência de limite de tamanho em `content` do chat

`POST /projects/{id}/chat/sessions/{session_id}/messages` aceita `request.content` sem limite de tamanho. O conteúdo é:
- Armazenado no arquivo de sessão JSON em disco.
- Interpolado no prompt enviado ao agente (histórico das últimas 12 mensagens).
- Potencialmente enviado à API de LLM, gerando custo de tokens.

Payloads grandes podem causar consumo excessivo de tokens, lentidão e crescimento ilimitado de arquivos de sessão.

**Localização:** `routes_chat.py:124`, `chat_service.py:39`

#### 2. `resolution_summary` sem limite em issue resolve

`POST /projects/{id}/issues/resolve` aceita `request.resolution_summary` sem validação de tamanho. O valor é persistido no `activity.jsonl` e propagado para `issues.json`.

**Localização:** `routes_issues.py:40`

#### 3. `run_id` sem validação de formato

`GET /projects/{id}/logs/stream/{run_id}` recebe `run_id` como path parameter sem validar que é um UUID válido antes de usar como chave em `LogStreamer._logs`. Não causa path traversal (store é in-memory), mas cria ruído de estado.

**Localização:** `routes_logs.py:9`

#### 4. `agent_id` persistido antes de validação

Em `routes_chat.py:create_chat_session`, `agent_id` é armazenado na sessão sem validação prévia. Sessões com `agent_id` inválido são criadas normalmente e só falham ao enviar mensagens.

**Localização:** `routes_chat.py:83-89`

---

## IV-007 — Sanitização Ausente

**Status: FAIL — HIGH**

### Achado Principal: Path Traversal via `session_id`

`backend/app/core/chat_store.py` constrói o caminho do arquivo diretamente a partir do `session_id` fornecido pelo usuário, sem nenhuma validação de traversal:

```python
# chat_store.py:49-52
def load_session(self, session_id: str) -> dict[str, Any] | None:
    path = self.sessions_dir / f"{session_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

# chat_store.py:60-64
def delete_session(self, session_id: str) -> bool:
    path = self.sessions_dir / f"{session_id}.json"
    if not path.exists():
        return False
    path.unlink()
    return True
```

**Exemplo de exploração:**

```
GET /api/v1/projects/ESAA-supervisor/chat/sessions/../../roadmap
```

Path resultante: `.roadmap/chat_sessions/../../roadmap.json` → `.roadmap/roadmap.json`

O arquivo existe, é lido e seu conteúdo retornado na resposta da API como se fosse uma sessão de chat.

```
DELETE /api/v1/projects/ESAA-supervisor/chat/sessions/../../roadmap
```

**Deleta `.roadmap/roadmap.json`** — destruição do artefato principal do projeto.

**Arquivos alcançáveis via traversal a partir de `sessions_dir`:**

| Arquivo | Via session_id | Impacto |
|---------|---------------|---------|
| `.roadmap/roadmap.json` | `../../roadmap` | Leitura / Deleção |
| `.roadmap/roadmap.security.json` | `../../roadmap.security` | Leitura / Deleção |
| `.roadmap/issues.json` | `../../issues` | Leitura / Deleção |
| `.roadmap/lessons.json` | `../../lessons` | Leitura / Deleção |

**Severidade: HIGH** — permite leitura e deleção de artefatos canônicos do projeto via API autenticada apenas por project_id.

### Achado Secundário: Metadados Internos Expostos em API

`AgentResult.metadata` inclui `"command": command` — a lista completa de argumentos do subprocess, incluindo caminhos absolutos de instalação dos agentes. Esse dado é retornado via `GET /projects/{id}/runs/{run_id}` e exposto ao frontend.

```json
{
  "metadata": {
    "command": ["C:\\Users\\...\\npm\\claude.cmd", "-p", "--output-format", "json", "--permission-mode", "bypassPermissions"],
    "stdout": "...",
    "stderr": "..."
  }
}
```

Revela estrutura interna, caminhos de instalação e flags de permissão usados pelo sistema.

---

## Checklist de Aceite

| Item | Status |
|------|--------|
| IV-001 SQL Injection auditado | N/A confirmado |
| IV-002 Command Injection auditado | PASS com ressalvas |
| IV-003 Template/Prompt Injection auditado | FAIL — MEDIUM |
| IV-004 SSRF auditado | N/A (risco indireto) |
| IV-005 XSS auditado | PASS |
| IV-006 Inputs não validados auditados | PARTIAL — MEDIUM |
| IV-007 Sanitização ausente auditada | FAIL — HIGH (path traversal) |
| Path traversal em `chat_store.py` identificado | SIM |
| Prompt injection via `chat_service.py` identificado | SIM |
| Relatório `reports/phase2/results/SEC-015.json` gerado | SIM |

---

## Limitações Conhecidas

- Auditoria é estática (code review). Não foram executados testes dinâmicos contra instância live.
- Agentes de terceiros (codex, gemini-cli) não foram auditados internamente — apenas sua interface de integração.
- Dependências de frontend (node_modules) não foram auditadas neste playbook (coberto por SEC-005/SEC-006).
- O path traversal exige que `sessions_dir` exista e que o arquivo alvo tenha extensão `.json`. Arquivos `.jsonl` (activity.jsonl) não são alcançáveis.

---

## Smoke Report

- Codebase lido: backend Python (FastAPI) + frontend TypeScript (React). Total de ~35 arquivos Python e ~55 arquivos TSX.
- Nenhum SQL, ORM ou driver de banco encontrado → IV-001 N/A confirmado.
- `subprocess.run` encontrado em 2 arquivos (`base.py`, `chat_service.py`), ambos sem `shell=True` → IV-002 PASS.
- `session_id` em `chat_store.py` sem validação de path traversal → **IV-007 HIGH** confirmado.
- `user_message` interpolado diretamente no prompt LLM com agentes em modo `bypassPermissions`/`yolo` → **IV-003 MEDIUM** confirmado.
- `dangerouslySetInnerHTML` e `eval()` ausentes no frontend → IV-005 PASS confirmado.
- Inputs de `content` e `resolution_summary` sem limite de tamanho → IV-006 PARTIAL confirmado.
