# Auditoria de Criptografia - SEC-018

## Resumo Executivo

A auditoria de criptografia no sistema **ESAA-supervisor (PoC)** avaliou cinco domínios conforme o playbook CR-001 a CR-005. O sistema não utiliza criptografia ativa exceto pelo hash SHA-256 para verificação de integridade da projeção de roadmap. Não há HTTPS configurado, nenhum dado é criptografado em repouso, e não existe política de rotação de chaves. Dado o contexto de PoC local sem exposição à internet, o risco imediato é baixo, mas os padrões não atendem a requisitos de produção.

---

## Detalhes dos Checks (Playbook CR-001 a CR-005)

| ID | Check | Status | Severidade | Evidência / Observação |
| --- | --- | --- | --- | --- |
| CR-001 | HTTPS obrigatório | **FAIL** | HIGH | Backend configurado em HTTP (`ESAA_HOST=127.0.0.1`, porta 8000). Frontend usa `http://localhost:8000`. Nenhum middleware de redirecionamento HTTPS ou configuração TLS/SSL encontrada em `main.py` ou configuração FastAPI. |
| CR-002 | Algoritmos criptográficos | **PASS** | — | SHA-256 via `hashlib.sha256()` (Python stdlib) em `projector.py:160`. Aplicado sobre JSON canônico com `sort_keys=True`. Nenhum algoritmo fraco (MD5, SHA-1) encontrado na codebase. Ausência de criptografia simétrica/assimétrica — coerente com o escopo do PoC. |
| CR-003 | Encryption at-rest | **FAIL** | MEDIUM | Todos os artefatos ESAA armazenados em texto plano: `roadmap.json`, `activity.jsonl`, `issues.json`, `lessons.json` e sessões de chat em `.roadmap/chat_sessions/*.json`. Nenhuma camada de criptografia de arquivo ou banco de dados encontrada. |
| CR-004 | Chaves expostas | **PARTIAL** | MEDIUM | Nenhuma chave API hardcoded no código-fonte. Backend `.env` contém apenas variáveis operacionais (`ESAA_ENV`, `ESAA_HOST`, `ESAA_PORT`, `ESAA_ROADMAP_DIR`). Chaves de agentes (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY) são injetadas via `os.environ.copy()` em `base.py:65`. Falha parcial: (1) o array `command` com caminhos internos do executável é retornado na resposta da API de chat (`chat_service.py:158`); (2) ausência de `.gitignore` na raiz do repositório — arquivos `.env` podem ser acidentalmente versionados. |
| CR-005 | Rotação de chaves | **FAIL** | LOW | Sem mecanismo de rotação de chaves. Chaves API são variáveis de ambiente sem ciclo de vida gerenciado. Não há sistema de gerenciamento de segredos (Vault, AWS Secrets Manager, etc.). Sem tokens de sessão e, portanto, sem rotação de sessão. |

---

## Análise de Risco

### 1. Ausência de HTTPS (CR-001)

O backend FastAPI não configura SSL/TLS. O arquivo `backend/.env` define `ESAA_HOST=127.0.0.1` e `ESAA_PORT=8000`, e o frontend aponta para `http://localhost:8000`. Em modo de desenvolvimento local isso é aceitável, mas a ausência de qualquer configuração de HTTPS no código impede o deploy seguro em produção sem intervenção de infraestrutura (proxy reverso com Nginx/Caddy).

**Arquivo relevante**: `backend/app/main.py` — sem middleware SSL, sem `ssl_keyfile`/`ssl_certfile` no Uvicorn.

### 2. Dados em repouso sem criptografia (CR-003)

O `ChatStore` persiste histórico de conversas com agentes LLM em `chat_sessions/*.json` com `path.write_text(..., encoding="utf-8")` sem qualquer envelope criptográfico. Prompts e respostas de agentes, que podem conter código, paths internos e outputs de execução, ficam expostos a qualquer usuário com acesso ao filesystem.

**Arquivo relevante**: `backend/app/core/chat_store.py:57`.

### 3. Vazamento de metadados de comando (CR-004)

A resposta da API de chat inclui o campo `"command"` no metadata (`chat_service.py:158`), que contém o array de strings com o caminho completo do executável do agente (ex: `["C:\\Users\\...\\AppData\\Roaming\\npm\\claude.cmd", "-p", ...]`). Isso expõe estrutura interna do sistema e caminhos absolutos ao consumidor da API.

### 4. Ausência de .gitignore raiz (CR-004)

Não foi encontrado `.gitignore` na raiz do repositório (apenas em `.pytest_cache/`). Os arquivos `backend/.env` e `frontend/.env` contêm valores de configuração que, se contivessem chaves API, seriam acidentalmente versionados.

### 5. SHA-256 — Uso correto (CR-002)

O único uso criptográfico ativo é o hash de projeção em `projector.py`:

```python
canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

O algoritmo é adequado (SHA-256), a entrada é determinística (JSON canônico com `sort_keys=True`) e o resultado é usado para detecção de adulteração do roadmap. Não há colisão por design — o hash protege integridade, não confidencialidade.

---

## Recomendações

1. **HTTPS em produção**: Documentar que o deploy em produção requer proxy reverso (Nginx, Caddy ou Traefik) com terminação TLS. Adicionar aviso no README e bloquear inicialização se `ESAA_ENV=production` sem variável `ESAA_TLS_ENABLED=true`.
2. **Omitir `command` da resposta de API**: Remover ou filtrar o campo `"command"` do metadata retornado pela API de chat (`chat_service.py:158`) para evitar exposição de caminhos internos.
3. **Adicionar `.gitignore` raiz**: Criar `.gitignore` na raiz do repositório com regras para `*.env`, `.env.*`, `*.key`, `*.pem`, `chat_sessions/` e outros artefatos sensíveis.
4. **Encryption at-rest (roadmap para produção)**: Para deploy além de PoC local, considerar `cryptography.fernet` para criptografar arquivos de sessão de chat ou usar um banco de dados com criptografia nativa.
5. **Gestão de chaves**: Documentar uso de variáveis de ambiente e considerar integração com um gerenciador de segredos para ambientes compartilhados.

---

Auditoria realizada por: claude-sonnet-4-6
Data: 2026-03-07
Task: SEC-018
Status: complete
