# Auditoria de Headers de Seguranca - SEC-019

## Resumo Executivo

A auditoria de headers de seguranca no sistema **ESAA-supervisor (PoC)** avaliou cinco controles do playbook `security_headers` (`SH-001` a `SH-005`): `Content-Security-Policy`, `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options` e `Referrer-Policy`.

Nao foi encontrada configuracao explicita desses headers no backend FastAPI nem no frontend Vite. Em validacao de runtime, uma requisicao HTTP para `http://127.0.0.1:8000/` retornou apenas `Date`, `Server`, `Content-Length` e `Content-Type`, confirmando a ausencia dos headers auditados na superficie real da API.

Como o projeto e uma PoC local, o impacto imediato e reduzido, mas o baseline atual nao atende a um padrao minimo de hardening para ambientes compartilhados ou producao.

---

## Detalhes dos Checks (Playbook SH-001 a SH-005)

| ID | Check | Status | Severidade | Evidencia / Observacao |
| --- | --- | --- | --- | --- |
| SH-001 | Content-Security-Policy (CSP) | **FAIL** | HIGH | Nenhum header `Content-Security-Policy` retornado pela API FastAPI em `http://127.0.0.1:8000/`. Tambem nao ha meta tag CSP em `frontend/index.html`, e `frontend/vite.config.ts` nao define headers de resposta. |
| SH-002 | Strict-Transport-Security (HSTS) | **FAIL** | MEDIUM | Nenhum header `Strict-Transport-Security` na resposta HTTP observada. O sistema opera em HTTP puro (`http://127.0.0.1:8000` e proxy Vite para `http://localhost:8000`), o que torna HSTS inexequivel no baseline atual. |
| SH-003 | X-Frame-Options | **FAIL** | MEDIUM | Nenhum header `X-Frame-Options` foi encontrado no runtime. Tambem nao existe protecao equivalente visivel por `frame-ancestors` em CSP, porque nao ha CSP configurada. |
| SH-004 | X-Content-Type-Options | **FAIL** | MEDIUM | Nenhum header `X-Content-Type-Options: nosniff` retornado pela API FastAPI. O backend nao adiciona middleware ou headers customizados em `backend/app/main.py`. |
| SH-005 | Referrer-Policy | **FAIL** | LOW | Nenhum header `Referrer-Policy` na resposta HTTP e nenhuma meta tag correspondente em `frontend/index.html`. O comportamento fica dependente do default do navegador. |

---

## Evidencia de Runtime

Requisicao real executada contra o backend local:

- URL: `http://127.0.0.1:8000/`
- Headers retornados: `Date`, `Server`, `Content-Length`, `Content-Type`
- Headers ausentes entre os auditados: `Content-Security-Policy`, `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`

---

## Analise Tecnica

### 1. Backend sem middleware de hardening

O arquivo `backend/app/main.py` instancia o `FastAPI` e adiciona apenas `CORSMiddleware`, com `allow_origins=["*"]`, `allow_methods=["*"]` e `allow_headers=["*"]`. Nao ha middleware responsavel por anexar headers de seguranca nas respostas.

### 2. Frontend sem politica de cabecalhos ou meta fallback

O arquivo `frontend/index.html` contem apenas metadados basicos (`charset`, `viewport` e `title`). Nao ha meta tag CSP nem meta `referrer`.

O arquivo `frontend/vite.config.ts` define porta e proxy de desenvolvimento, mas nao configura headers de resposta para o servidor dev.

### 3. Ausencia de camadas equivalentes

Sem CSP, a aplicacao tambem perde a alternativa moderna a `X-Frame-Options` via diretiva `frame-ancestors`. Assim, a ausencia nao e apenas de headers legados isolados; falta uma politica coerente de isolamento do browser.

### 4. HSTS bloqueado pelo baseline atual

O achado de HSTS e estruturalmente ligado ao achado anterior de criptografia (`SEC-018`): como o sistema nao oferece HTTPS, o header `Strict-Transport-Security` nao pode ser corretamente aplicado. Em outras palavras, HSTS esta ausente e o stack atual tambem nao suporta sua ativacao segura.

---

## Recomendacoes

1. Adicionar middleware de seguranca no backend para anexar `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options` e `Referrer-Policy` a todas as respostas HTTP relevantes.
2. Definir uma CSP minima para a PoC, por exemplo restringindo `default-src 'self'`, `frame-ancestors 'none'`, `object-src 'none'` e ajustando `connect-src` para o backend local.
3. Migrar o deploy nao-local para HTTPS via proxy reverso e so entao habilitar `Strict-Transport-Security`.
4. Definir `X-Frame-Options: DENY` ou proteger por `frame-ancestors 'none'` na CSP, evitando clickjacking.
5. Definir `X-Content-Type-Options: nosniff` e `Referrer-Policy: strict-origin-when-cross-origin` como baseline minimo.

---

Auditoria realizada por: codex
Data: 2026-03-08
Task: SEC-019
Status: complete
