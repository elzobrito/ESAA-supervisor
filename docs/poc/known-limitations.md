# ESAA Supervisor PoC — Limitações Conhecidas e Próximos Passos

**Versão:** 1.0
**Data:** 2026-03-07

---

## 1. Limitações de Escopo

### 1.1 Single-user, single-project

A PoC suporta apenas **um projeto ativo** por instância do backend. O `CanonicalStore` é um singleton em memória; múltiplos projetos requerem refatoração do roteamento e isolamento de estado.

**Impacto:** Não há suporte a times ou projetos paralelos.
**Mitigação planejada:** Instanciar `CanonicalStore` por projeto_id no escopo da request (DI container).

---

### 1.2 Execução de agente é um stub

O `RunEngine` simula a execução do agente com um `asyncio.sleep`. A integração real com Gemini-CLI, Claude Code ou outro agente **não está implementada**.

**Impacto:** Runs sempre terminam com `status: done` após delay fixo, independentemente do agente.
**Mitigação planejada:** Implementar `AgentDriver` com interface abstrata; primeira implementação: subprocess + stdin/stdout.

---

### 1.3 Sem autenticação

Todos os endpoints são públicos. Qualquer cliente na rede local pode iniciar, cancelar ou consultar runs.

**Impacto:** Adequado apenas para uso local isolado.
**Mitigação planejada:** API key via header `X-ESAA-Token` ou OAuth2 para ambientes compartilhados.

---

### 1.4 Gravações concorrentes no event store (ISS-0002)

O `activity.jsonl` é append-only, mas não há serialização atômica entre processos. Escritas concorrentes de múltiplos agentes podem quebrar a monotonicity de `event_seq`.

**Impacto:** Alto risco em cenários multi-agente ou multi-processo.
**Mitigação atual:** `ProjectLock` por projeto (in-process); operação single-writer na PoC.
**Mitigação planejada:** Usar `fcntl.flock` (Linux) ou lock de arquivo nomeado (Windows) antes de cada append.

---

### 1.5 `verify_status` não é recomputado automaticamente

O campo `verify_status` em `roadmap.json` pode mostrar `mismatch` após atualizações manuais do roadmap, pois a reprojeção de hash não é executada automaticamente.

**Impacto:** Auditoria de integridade reporta divergência mesmo quando o estado é válido.
**Mitigação planejada:** Executar `Projector.compute_projection_hash()` e atualizar `roadmap.json` após cada evento persistido pelo `EventWriter`.

---

### 1.6 SSE (streaming de logs) não testado end-to-end via smoke

O endpoint `GET /runs/{id}/logs` (Server-Sent Events) é coberto por testes unitários com mocks, mas não é exercitado pelo smoke script (`run_poc_smoke.sh`), pois requer um `EventSource` client.

**Impacto:** Não há evidência automatizada de que o streaming funciona com um cliente real.
**Mitigação planejada:** Adicionar passo de smoke usando `curl -N` para verificar que o content-type é `text/event-stream`.

---

### 1.7 Frontend não tem hot-reload em produção

O build de produção (`npm run build`) gera artefatos estáticos. Não há servidor de produção configurado (nginx, caddy etc.).

**Impacto:** Para uso não-dev é necessário configurar um servidor de arquivos estáticos apontando para `frontend/dist/`.
**Mitigação:** Use `npm run dev` para desenvolvimento local.

---

### 1.8 Dependência de ROADMAP_DIR hardcoded

O `routes_projects.py` resolve o diretório `.roadmap` como `../` relativo ao diretório de execução do uvicorn (`backend/`). Alterar o diretório de trabalho quebra o carregamento do projeto.

**Impacto:** O backend deve ser sempre iniciado a partir de `backend/`.
**Mitigação planejada:** Variável de ambiente `ESAA_ROADMAP_DIR` com fallback para `../. roadmap`.

---

### 1.9 Windows: `fuser` não disponível

O smoke script tenta matar processos na porta com `fuser`, que não existe no Windows.

**Impacto:** Em Windows, se a porta 8099 estiver ocupada, o script falha ao subir o backend. O kill manual via `taskkill` é necessário.
**Mitigação atual:** Script ignora falha do `fuser` e continua. Documentado no runbook.

---

## 2. Débitos Técnicos

| ID | Área | Descrição | Prioridade |
|---|---|---|---|
| TD-001 | Backend | `CanonicalStore` singleton — não escalável para multi-projeto | Alta |
| TD-002 | Backend | `RunEngine` sem integração real com agentes | Alta |
| TD-003 | Backend | Sem variável de ambiente para `ROADMAP_DIR` | Média |
| TD-004 | Backend | `verify_status` não atualizado automaticamente pós-evento | Média |
| TD-005 | Backend | Sem autenticação nos endpoints | Média |
| TD-006 | Frontend | Sem testes automatizados (Vitest/Playwright) | Média |
| TD-007 | Infra | Sem Dockerfile ou script de setup único | Baixa |
| TD-008 | Smoke | SSE não testado end-to-end | Baixa |

---

## 3. Próximos Passos Recomendados

### Curto prazo (antes de uso experimental)

1. **Implementar `AgentDriver`** com integração subprocess para Gemini-CLI
2. **Adicionar `ESAA_ROADMAP_DIR` env var** no backend
3. **Serialização de escritas** no `EventWriter` via file lock

### Médio prazo

4. **Testes E2E frontend** com Playwright (fluxo completo no browser)
5. **Multi-projeto** via DI container no FastAPI
6. **Autenticação básica** (API key) para acesso compartilhado

### Longo prazo

7. **Dashboard de auditoria** — visualização do event store com diff entre eventos
8. **Reprojeção automática** — trigger de `esaa verify` após cada write
9. **Suporte a rollback** — reverter roadmap.json a um snapshot anterior via replay do event store

---

## 4. Issues Abertas

| Issue | Severidade | Status | Título |
|---|---|---|---|
| ISS-0002 | High | Open | Concurrent writes to activity.jsonl break monotonicity |

Consulte `.roadmap/issues.json` para detalhes completos.

---

*Documento gerado por claude-code como parte de ESUP-QA-018.*
