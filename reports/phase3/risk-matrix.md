# Matriz de Riscos Consolidada

Este documento apresenta a matriz consolidada de vulnerabilidades identificadas durante a auditoria de segurança do sistema ESAA, categorizadas por domínio e ordenadas por severidade decrescente.

| ID | Vulnerabilidade | Categoria | Severidade | Impacto (CIA) | Recomendação |
|:---|:----------------|:----------|:-----------|:--------------|:-------------|
| SC-004 | CORS Permissivo | secrets_config | **CRITICAL** | C: HIGH, I: HIGH, A: LOW | Configurar uma lista restrita de domínios permitidos no CORSMiddleware. |
| SC-008 | Variáveis Sensíveis em Logs | secrets_config | **CRITICAL** | C: HIGH, I: LOW, A: LOW | Implementar sanitização de logs e autenticação para o endpoint de streaming. |
| AU-001 | Senhas armazenadas em texto plano | authentication | **CRITICAL** | C: HIGH, I: HIGH, A: MEDIUM | Implementar armazenamento seguro com bcrypt/argon2. |
| AZ-001 | Controle de acesso ausente | authorization | **CRITICAL** | C: HIGH, I: HIGH, A: MEDIUM | Implementar middleware de autenticação (JWT/Session) em todas as rotas da API. |
| AZ-002 | IDOR (Insecure Direct Object Reference) | authorization | **CRITICAL** | C: HIGH, I: HIGH, A: MEDIUM | Restringir o escopo de navegação a um diretório de dados específico (sandboxing). |
| AZ-003 | Verificação de permissão apenas no frontend | authorization | **CRITICAL** | C: HIGH, I: HIGH, A: MEDIUM | Implementar lógica de autorização no backend e refletir roles no frontend para controle de UI. |
| LM-001 | Logs contendo dados sensíveis | logging_monitoring | **CRITICAL** | C: LOW, I: LOW, A: LOW | Implement a regex-based redaction filter in the LogStreamer class to mask sensitive patterns before streaming and storage. |
| AI-001 | Prompt injection possível | ai_llm_security | **CRITICAL** | C: HIGH, I: HIGH, A: HIGH | Use secure delimiters (e.g., XML tags) and implement prompt injection detection filters. |
| AI-002 | LLM com acesso irrestrito a ferramentas | ai_llm_security | **CRITICAL** | C: HIGH, I: HIGH, A: HIGH | Disable YOLO/bypass modes and implement explicit human approval for destructive or high-risk tool calls. |
| AU-002 | Hash de senha inseguro | authentication | **HIGH** | C: HIGH, I: HIGH, A: MEDIUM | Adicionar biblioteca passlib ou similar para hashing seguro. |
| AU-004 | Reset de senha inseguro | authentication | **HIGH** | C: HIGH, I: HIGH, A: MEDIUM | Implementar fluxo de reset com tokens seguros e expiracao. |
| AU-005 | Sessoes sem expiração | authentication | **HIGH** | C: HIGH, I: HIGH, A: MEDIUM | Implementar sessoes com TTL e cookies HttpOnly/Secure. |
| AU-006 | Ausência de proteção contra brute force | authentication | **HIGH** | C: HIGH, I: HIGH, A: MEDIUM | Adicionar middleware de rate limiting (ex: slowapi). |
| AU-007 | Tokens permanentes | authentication | **HIGH** | C: HIGH, I: HIGH, A: MEDIUM | Utilizar JWT com tempo de expiracao curto e refresh tokens. |
| AU-008 | Session fixation | authentication | **HIGH** | C: HIGH, I: HIGH, A: MEDIUM | Regenerar ID de sessao apos login. |
| AZ-004 | Admin routes expostas | authorization | **HIGH** | C: HIGH, I: HIGH, A: MEDIUM | Proteger rotas operacionais com controle de acesso baseado em roles (RBAC). |
| AP-001 | Endpoints sem rate limit | api_security | **HIGH** | C: LOW, I: LOW, A: HIGH | Implementar middleware de rate limiting no FastAPI (ex: slowapi) e aplicar limites especificos por endpoint e IP. |
| IV-007 | Sanitização Ausente | input_validation | **HIGH** | C: HIGH, I: HIGH, A: MEDIUM | Validate session_id matches UUID format before constructing file path. Optionally resolve path and assert it stays within sessions_dir. Strip or omit command array from public API responses. |
| FU-001 | Uploads sem validação de tipo | file_upload | **HIGH** | C: LOW, I: LOW, A: LOW |  |
| FU-005 | Possibilidade de upload executável | file_upload | **HIGH** | C: LOW, I: LOW, A: LOW |  |
| SS-001 | Cookies sem httpOnly | session_security | **HIGH** | C: LOW, I: LOW, A: LOW | Implementar cookies HttpOnly para sessoes de autenticacao e chat. |
| SS-002 | Cookies sem Secure flag | session_security | **HIGH** | C: LOW, I: LOW, A: LOW | Configurar Secure=True em todos os cookies sensiveis. |
| SS-005 | Sessões sem expiração | session_security | **HIGH** | C: LOW, I: LOW, A: LOW | Implementar expiraÃ§Ã£o (TTL) e rotina de limpeza de sessoes. |
| CR-001 | HTTPS obrigatório | cryptography | **HIGH** | C: HIGH, I: MEDIUM, A: LOW |  |
| SH-001 | Content-Security-Policy (CSP) | security_headers | **HIGH** | C: MEDIUM, I: MEDIUM, A: LOW |  |
| IF-001 | HTTPS / TLS termination | infrastructure | **HIGH** | C: MEDIUM, I: MEDIUM, A: MEDIUM |  |
| IF-005 | Backups | infrastructure | **HIGH** | C: LOW, I: HIGH, A: HIGH |  |
| DO-003 | Secrets scanning ausente | devsecops | **HIGH** | C: MEDIUM, I: MEDIUM, A: LOW | Integrar gitleaks ou trufflehog na CI/CD. Adicionar hook de pre-commit para validação local de segredos. |
| DA-003 | Retention Policy | unknown | **HIGH** | C: HIGH, I: MEDIUM, A: LOW |  |
| DA-005 | LGPD/GDPR Compliance | unknown | **HIGH** | C: HIGH, I: MEDIUM, A: LOW |  |
| AI-003 | Ausência de filtragem de input | ai_llm_security | **HIGH** | C: LOW, I: LOW, A: LOW | Implement input moderation, rate limiting, and maximum context window constraints. |
| AI-004 | Possibilidade de exfiltração de dados | ai_llm_security | **HIGH** | C: LOW, I: LOW, A: LOW | Sanitize LLM output to strip external links or images and use output guardrails to prevent system prompt leakage. |
| SC-003 | Arquivos Sensíveis Expostos | secrets_config | MEDIUM | C: LOW, I: LOW, A: LOW | Adicionar .gitignore na raiz do projeto com exclusões adequadas. |
| SC-005 | Modo Debug Enabled | secrets_config | MEDIUM | C: LOW, I: LOW, A: LOW | Utilizar log level info em ambientes de produção. |
| DS-001 | Dependências com vulnerabilidades conhecidas | dependencies_supply_chain | MEDIUM | C: LOW, I: LOW, A: LOW | Atualizar vite para >= 7.3.1 no frontend. |
| AU-003 | Ausencia de MFA | authentication | MEDIUM | C: MEDIUM, I: MEDIUM, A: LOW | Integrar TOTP/2FA. |
| AZ-005 | Escopo de permissões mal definido | authorization | MEDIUM | C: HIGH, I: HIGH, A: MEDIUM | Definir matriz de permissões (ex: Admin, Operator, Auditor) e implementar enforcement. |
| AP-002 | Endpoints retornando dados excessivos | api_security | MEDIUM | C: MEDIUM, I: MEDIUM, A: LOW | Utilizar DTOs mais enxutos, filtrar campos sensiveis e implementar carregamento sob demanda para listas grandes. |
| AP-003 | Enumeração de usuários | api_security | MEDIUM | C: MEDIUM, I: MEDIUM, A: LOW | Restringir o BROWSE_ROOT a um diretorio de dados isolado e validar rigorosamente os caminhos acessados. |
| AP-006 | Ausência de paginação | api_security | MEDIUM | C: MEDIUM, I: MEDIUM, A: LOW | Implementar paginacao obrigatoria em todos os endpoints que retornam listas, com limites default e maximos. |
| AP-007 | Replay attacks possíveis | api_security | MEDIUM | C: MEDIUM, I: MEDIUM, A: LOW | Implementar suporte a headers de idempotencia (ex: X-Idempotency-Key) para todas as operacoes de escrita (POST/PUT/DELETE). |
| IV-003 | Template Injection / Prompt Injection | input_validation | MEDIUM | C: LOW, I: LOW, A: LOW | Delimit user content with structural markers (XML tags). Evaluate if bypassPermissions/yolo is needed for interactive chat sessions. |
| IV-006 | Inputs Não Validados | input_validation | MEDIUM | C: LOW, I: LOW, A: LOW | Add Field(..., max_length=N) to Pydantic models for free-text inputs. Validate agent_id on session creation. |
| FU-002 | Uploads sem limite de tamanho | file_upload | MEDIUM | C: LOW, I: LOW, A: LOW |  |
| FU-004 | Ausência de antivírus | file_upload | MEDIUM | C: LOW, I: LOW, A: LOW |  |
| SS-003 | SameSite ausente | session_security | MEDIUM | C: LOW, I: LOW, A: LOW | Configurar SameSite=Strict em cookies de sessao. |
| SS-006 | Tokens reutilizáveis | session_security | MEDIUM | C: LOW, I: LOW, A: LOW | Implementar rotaca§Ã£o de IDs de sessao e invalidacao manual. |
| CR-003 | Encryption at-rest | cryptography | MEDIUM | C: HIGH, I: MEDIUM, A: LOW |  |
| CR-004 | Chaves expostas | cryptography | MEDIUM | C: HIGH, I: MEDIUM, A: LOW |  |
| SH-002 | Strict-Transport-Security (HSTS) | security_headers | MEDIUM | C: MEDIUM, I: MEDIUM, A: LOW |  |
| SH-003 | X-Frame-Options | security_headers | MEDIUM | C: MEDIUM, I: MEDIUM, A: LOW |  |
| SH-004 | X-Content-Type-Options | security_headers | MEDIUM | C: MEDIUM, I: MEDIUM, A: LOW |  |
| LM-004 | Ausência de alertas de segurança | logging_monitoring | MEDIUM | C: LOW, I: LOW, A: LOW | Integrate a central alerting service to notify operators of integrity failures or system crashes. |
| IF-002 | Firewall / regras de rede | infrastructure | MEDIUM | C: MEDIUM, I: MEDIUM, A: MEDIUM |  |
| IF-003 | WAF (Web Application Firewall) | infrastructure | MEDIUM | C: MEDIUM, I: MEDIUM, A: MEDIUM |  |
| IF-004 | Segmentação de rede | infrastructure | MEDIUM | C: MEDIUM, I: MEDIUM, A: MEDIUM |  |
| IF-006 | Proteção DDoS | infrastructure | MEDIUM | C: MEDIUM, I: MEDIUM, A: MEDIUM |  |
| DO-001 | Ausência de code review | devsecops | MEDIUM | C: MEDIUM, I: MEDIUM, A: LOW | Configurar branch protection no GitHub/GitLab. Exigir reviews obrigatórios para áreas críticas via CODEOWNERS. |
| DO-002 | Pipeline sem análise de segurança | devsecops | MEDIUM | C: MEDIUM, I: MEDIUM, A: LOW | Implementar esteira de CI/CD (ex: GitHub Actions) com validações de segurança em cada Pull Request. |
| DO-004 | SAST não implementado | devsecops | MEDIUM | C: MEDIUM, I: MEDIUM, A: LOW | Adicionar Semgrep e linters de segurança (ex: bandit para Python, eslint-plugin-security para JS) ao pipeline de desenvolvimento. |
| DO-006 | Deploy sem auditoria | devsecops | MEDIUM | C: MEDIUM, I: MEDIUM, A: LOW | Desenvolver scripts de deploy automatizados que gerem uma trilha de auditoria persistente ligada aos commits do repositório. |
| DA-001 | PII Protection | unknown | MEDIUM | C: LOW, I: LOW, A: LOW |  |
| DA-002 | Data Minimization | unknown | MEDIUM | C: LOW, I: LOW, A: LOW |  |
| FE-003 | Vulnerable JavaScript dependencies | unknown | MEDIUM | C: LOW, I: LOW, A: LOW |  |
| AI-005 | Logs de decisão da IA inexistentes | ai_llm_security | MEDIUM | C: LOW, I: LOW, A: LOW | Implement structured event sourcing (ESAA) for all agent tool choices and internal reasoning steps. |
| SC-007 | Configs de Exemplo | secrets_config | LOW | C: LOW, I: LOW, A: LOW | Garantir que .env.example contenha apenas placeholders. |
| AZ-006 | Ações sensíveis sem confirmação | authorization | LOW | C: HIGH, I: HIGH, A: MEDIUM | Adicionar steps de confirmação no frontend para todas as ações mutativas críticas. |
| CR-005 | Rotação de chaves | cryptography | LOW | C: HIGH, I: MEDIUM, A: LOW |  |
| SH-005 | Referrer-Policy | security_headers | LOW | C: MEDIUM, I: MEDIUM, A: LOW |  |
| LM-005 | Ausência de correlação de requisições | logging_monitoring | LOW | C: LOW, I: LOW, A: LOW | Add correlation ID middleware to FastAPI and propagate the ID to all downstream logging calls. |
| DO-005 | DAST não implementado | devsecops | LOW | C: MEDIUM, I: MEDIUM, A: LOW | Implementar scan dinâmico (ZAP) em ambiente de staging antes de qualquer deploy em produção. |
| DA-004 | Anonymization / Pseudonymization | unknown | LOW | C: LOW, I: LOW, A: LOW |  |
