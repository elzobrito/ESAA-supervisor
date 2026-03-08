# Auditoria de Infraestrutura - SEC-021

## Resumo Executivo

A auditoria de infraestrutura no sistema **ESAA-supervisor (PoC)** avaliou seis domínios conforme o playbook IF-001 a IF-006: HTTPS, firewall, WAF, segmentação de rede, backups e proteção DDoS.

O sistema é um **PoC local monorepo** sem nenhuma infraestrutura de produção configurada. Não existem arquivos `docker-compose.yml`, `Dockerfile`, `nginx.conf`, `k8s/` ou `terraform/` no repositório. O backend (FastAPI/Uvicorn) e o frontend (Vite dev server) rodam diretamente na máquina local na interface `127.0.0.1`. Todos os seis domínios avaliados resultam em **FAIL** ou **N/A-risco**, com severidade reduzida dado o contexto exclusivamente local. Os riscos identificados são relevantes apenas no momento de qualquer deploy além do localhost.

---

## Detalhes dos Checks (Playbook IF-001 a IF-006)

| ID | Check | Status | Severidade | Evidência / Observação |
| --- | --- | --- | --- | --- |
| IF-001 | HTTPS / TLS termination | **FAIL** | HIGH (produção) / LOW (PoC local) | Sem proxy reverso (Nginx, Caddy, Traefik) e sem configuração TLS no Uvicorn. `backend/.env`: `ESAA_HOST=127.0.0.1`, `ESAA_PORT=8000`. Frontend: `VITE_API_BASE_URL=http://localhost:8000`. Tráfego em HTTP puro. Nenhum arquivo `nginx.conf` ou equivalente no repositório. |
| IF-002 | Firewall / regras de rede | **FAIL** | MEDIUM (produção) / INFO (PoC local) | Sem regras de firewall de aplicação ou de sistema operacional configuradas no repositório. Backend exposto em `0.0.0.0` (ou `127.0.0.1`) sem restrição de IP de origem documentada. Ausência de `iptables`, `ufw` ou equivalente Windows Firewall configurado via código. |
| IF-003 | WAF (Web Application Firewall) | **FAIL** | MEDIUM (produção) / INFO (PoC local) | Sem WAF configurado. Nenhum middleware FastAPI de bloqueio de padrões maliciosos, nenhum serviço de borda (Cloudflare WAF, AWS WAF, ModSecurity). Requisições maliciosas chegam diretamente ao backend sem filtragem. |
| IF-004 | Segmentação de rede | **FAIL** | MEDIUM (produção) / INFO (PoC local) | Arquitetura não segmentada: frontend dev server (porta 5173) e backend API (porta 8000) rodam na mesma máquina sem isolamento de rede. Sem Docker network, sem VLAN, sem namespace de rede. CORS configurado como `allow_origins=["*"]` em `backend/app/main.py:29`. |
| IF-005 | Backups | **FAIL** | HIGH | Sem mecanismo de backup para os artefatos ESAA críticos: `activity.jsonl` (event store), `roadmap.json`, `issues.json`, `lessons.json`. Não existe cron job, script de backup ou política de retenção documentada. Perda do `activity.jsonl` é irrecuperável — destrói a trilha de auditoria e impossibilita reprojeção. |
| IF-006 | Proteção DDoS | **FAIL** | MEDIUM (produção) / INFO (PoC local) | Sem proteção DDoS em nenhuma camada. Sem rate limiting de infraestrutura (apenas ausência de rate limiting de aplicação, já documentado em SEC-014). Sem CDN, sem mitigação volumétrica. Backend FastAPI exposto diretamente sem nenhum intermediário de borda. |

---

## Análise de Risco

### 1. Ausência de HTTPS / TLS (IF-001)

O backend roda exclusivamente em HTTP. O arquivo `backend/.env` confirma:

```
ESAA_HOST=127.0.0.1
ESAA_PORT=8000
```

O frontend configura `VITE_API_BASE_URL=http://localhost:8000`. O código `backend/app/main.py` instancia `FastAPI` sem `ssl_keyfile` ou `ssl_certfile`. Não há arquivo `nginx.conf`, `caddy.json` ou equivalente no repositório para terminar TLS externamente.

Em contexto de PoC local o risco é baixo. Para qualquer deploy em rede compartilhada, all API calls — incluindo prompts LLM, tokens e dados de agentes — trafegam em texto plano.

**Observação de sobreposição**: CR-001 (SEC-018) documenta o mesmo achado do ponto de vista de criptografia de transporte. Este check aborda a camada de infraestrutura (proxy reverso, terminação TLS).

### 2. Backups ausentes (IF-005)

Este é o achado de maior severidade independente do contexto de PoC. O `activity.jsonl` é o **event store imutável canônico** do sistema ESAA. Toda a lógica de projeção, auditoria e integridade depende deste arquivo.

Não existe:
- Backup automático (cron, script)
- Política de retenção
- Snapshot antes de runs
- Cópia redundante em storage separado

Corrupção ou exclusão acidental do `activity.jsonl` resulta em perda irrecuperável de toda a trilha de execução.

**Arquivos sem backup documentado**:
- `.roadmap/activity.jsonl`
- `.roadmap/roadmap*.json`
- `.roadmap/issues.json`
- `.roadmap/lessons.json`
- `.roadmap/chat_sessions/*.json`

### 3. CORS permissivo e ausência de segmentação (IF-004)

`backend/app/main.py:29` configura `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`. Combinado com a ausência de autenticação (documentado em SEC-012/SEC-013), qualquer página web em qualquer origem pode fazer requisições autenticadas à API do supervisor, incluindo iniciar runs de agentes.

### 4. Ausência de firewall e WAF (IF-002, IF-003)

Sem firewall, o backend está acessível a qualquer processo local (e potencialmente em rede se `ESAA_HOST` for alterado para `0.0.0.0`). Sem WAF, não há filtragem de padrões de ataque (SQLi, XSS, path traversal) em nível de infraestrutura — a defesa recai inteiramente na aplicação.

### 5. Sem proteção DDoS (IF-006)

Backend FastAPI exposto diretamente sem intermediário. O worker Uvicorn padrão (single process) pode ser exaurido por requisições concorrentes. Não há rate limiting de infraestrutura, queue de requisições nem mecanismo de circuit breaker.

---

## Recomendações

1. **IF-001 — HTTPS obrigatório em produção**: Para qualquer deploy além de localhost, provisionar proxy reverso (Nginx, Caddy ou Traefik) com terminação TLS. Adicionar aviso no README e bloquear start do backend se `ESAA_ENV=production` sem configuração TLS explícita.

2. **IF-005 — Backup do event store**: Implementar script de backup automático (ex: cron diário) para `.roadmap/activity.jsonl` e demais artefatos canônicos. Considerar backup pré-run como medida de segurança antes de mutações no estado.

3. **IF-004 — Restringir CORS**: Substituir `allow_origins=["*"]` por lista explícita de origens permitidas (`["http://localhost:5173"]` para dev). Em produção, apenas a origem do frontend.

4. **IF-002 — Documentar configuração de firewall**: Adicionar guia de hardening de rede ao README: bloquear portas 8000 e 5173 externamente, permitir apenas conexões locais ou de IPs específicos.

5. **IF-003 — WAF para produção**: Documentar requisito de WAF (Cloudflare, AWS WAF ou ModSecurity/Nginx) para deploy em ambiente exposto à internet.

6. **IF-006 — Rate limiting de infraestrutura**: Para deploy em produção, configurar Nginx com `limit_req_zone` ou equivalente. A camada de aplicação (FastAPI) também deve implementar rate limiting (gap já documentado em SEC-014).

---

## Contexto de Risco

A maior parte dos achados desta auditoria tem severidade **reduzida para o contexto atual** (PoC local, single-user, localhost). Os riscos se tornam **críticos** no momento de qualquer deploy em ambiente compartilhado, de rede ou cloud. A exceção é IF-005 (backups), que representa risco real imediato independente do contexto de deploy.

---

Auditoria realizada por: claude-sonnet-4-6
Data: 2026-03-08
Task: SEC-021
Status: complete
