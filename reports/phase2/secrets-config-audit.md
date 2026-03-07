# Auditoria de Segurança: Secrets & Configuração (SEC-010)

## 1. Sumário Executivo
A auditoria do domínio de **Secrets & Configuração** revelou uma postura de segurança permissiva, típica de uma Prova de Conceito (PoC), mas com vulnerabilidades críticas que impedem o uso em ambientes compartilhados ou produtivos. Os principais achados incluem a liberação total de CORS, ausência de autenticação em endpoints sensíveis (incluindo streaming de logs) e risco de exfiltração de segredos através da trilha de auditoria do ESAA.

## 2. Metodologia
A análise foi realizada através de:
- Varredura estática do código fonte (grep) em busca de padrões de segredos, chaves e credenciais.
- Inspeção manual de arquivos de configuração (`.env`, `main.py`, `log_stream.py`).
- Verificação de políticas de transporte e acesso (CORS, SSE).
- Análise do fluxo de dados de agentes para o event store (`activity.jsonl`).

## 3. Detalhamento por Check (Playbook: secrets_config)

| ID | Check | Status | Severidade | Achado |
|:---|:---|:---|:---|:---|
| SC-001 | Segredos Hardcoded | **PASS** | LOW | Nenhuma chave ou senha encontrada no código. |
| SC-002 | Chaves API no Frontend | **PASS** | LOW | Apenas URL base da API configurada via ambiente. |
| SC-003 | Arquivos Sensíveis Expostos | **FAIL** | MEDIUM | Ausência de `.gitignore` na raiz para proteger arquivos `.env`. |
| SC-004 | CORS Permissivo | **FAIL** | **CRITICAL** | `allow_origins=["*"]` configurado em `backend/app/main.py`. |
| SC-005 | Modo Debug Ativo | **PARTIAL** | MEDIUM | Runbook recomenda `--log-level debug`, o que aumenta verbosidade. |
| SC-006 | Credenciais Padrão | **N/A** | - | Sistema ainda não implementou banco de dados ou auth. |
| SC-007 | Configurações de Exemplo | **FAIL** | LOW | `.env` real e `.env.example` são idênticos e expõem portas/hosts. |
| SC-008 | Dados Sensíveis em Logs | **FAIL** | **CRITICAL** | Logs de agentes (stdout/stderr) são expostos via SSE sem auth. |

## 4. Vulnerabilidades Críticas

### [SC-004] CORS Totalmente Aberto
- **Arquivo:** `backend/app/main.py` (Linha 29)
- **Descrição:** A configuração `allow_origins=["*"]` permite que qualquer site execute requisições contra a API do Supervisor.
- **Impacto:** Um atacante pode induzir um usuário autenticado (ou operando localmente) a acessar um site malicioso que execute ações no Supervisor, como disparar execuções de agentes.
- **Recomendação:** Restringir `allow_origins` apenas aos domínios confiáveis do frontend.

### [SC-008] Exposição de Logs Sensíveis via SSE e Event Store
- **Arquivos:** `backend/app/api/routes_logs.py`, `backend/app/core/log_stream.py`, `.roadmap/activity.jsonl`
- **Descrição:** O output bruto dos agentes (stdout/stderr) é transmitido via SSE e persistido na trilha de auditoria. Não há sanitização ou mascaramento de dados sensíveis.
- **Impacto:** Se um agente (como o `codex` ou `gemini`) emitir uma chave de API ou segredo durante a execução, esse dado será transmitido sem criptografia/auth para o dashboard e ficará gravado permanentemente nos logs.
- **Recomendação:** Implementar camada de sanitização de segredos antes da persistência e streaming de logs.

## 5. Próximos Passos
1. Implementar `CORSMiddleware` com lista branca (whitelist).
2. Adicionar middleware de autenticação (ex: API Key simples para PoC).
3. Criar `.gitignore` robusto na raiz.
4. Introduzir filtros de regex para mascaramento de segredos em `BaseAgentAdapter`.
