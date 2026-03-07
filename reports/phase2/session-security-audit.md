# Auditoria de Segurança de Sessão - SEC-017

## Resumo Executivo
A auditoria de segurança de sessão no sistema **ESAA-supervisor (PoC)** identificou que o sistema não utiliza o mecanismo tradicional de sessões baseadas em cookies, optando por um modelo de identificadores de sessão (UUID) trafegados via parâmetros de rota (path parameters) para a funcionalidade de chat. Embora essa escolha mitigue ataques de CSRF tradicionais (que dependem do envio automático de cookies pelo navegador), a ausência de controles fundamentais como expiração de sessão, renovação de tokens e cabeçalhos de segurança de cookies (caso fossem adotados) representa uma lacuna crítica de segurança para um ambiente de produção.

## Detalhes dos Checks (Playbook SS-001 a SS-006)

| ID | Check | Status | Severidade | Evidência/Observação |
| --- | --- | --- | --- | --- |
| SS-001 | Cookies sem httpOnly | **FAIL** | HIGH | O sistema não utiliza cookies para gestão de sessão; a ausência de um mecanismo de cookie seguro é uma falha de design para proteção contra XSS. |
| SS-002 | Cookies sem Secure flag | **FAIL** | HIGH | Não há uso de cookies; a falta de imposição de transporte seguro para identificadores de sessão em produção é crítica. |
| SS-003 | SameSite ausente | **FAIL** | MEDIUM | Sem uso de cookies; a proteção nativa do browser contra CSRF via atributo SameSite não é aproveitada. |
| SS-004 | Ausência de CSRF token | **PASS/NA** | - | Mitigado pelo design: como não há cookies de autenticação, o navegador não envia credenciais automaticamente em requisições cross-site, impedindo ataques de CSRF tradicionais. |
| SS-005 | Sessões sem expiração | **FAIL** | HIGH | As sessões de chat (`ChatStore`) são persistentes no disco (`.roadmap/chat_sessions/*.json`) e não possuem tempo de expiração (TTL) ou limpeza automática de sessões inativas. |
| SS-006 | Tokens reutilizáveis | **FAIL** | MEDIUM | O `session_id` (UUIDv4) é permanente e reutilizável indefinidamente. Não há lógica de rotação de identificadores ou invalidação após período de inatividade. |

## Análise de Risco
O principal risco reside na **persistência indefinida de identificadores de sessão**. Uma vez que um `session_id` de chat é conhecido ou vazado (ex: via logs, histórico do navegador ou ombro de acesso), ele permite o acesso total ao histórico daquela sessão e a capacidade de enviar novas mensagens ao agente sem qualquer restrição temporal. 

Além disso, a configuração de CORS permissiva (`allow_origins=["*"]` com `allow_credentials=True` no `backend/app/main.py`) é uma "bomba-relógio": se o sistema for atualizado para usar cookies de sessão sem restringir as origens, ele se tornará imediatamente vulnerável a ataques de roubo de sessão cross-site.

## Recomendações
1. **Implementar TTL para Sessões**: Adicionar um campo `expires_at` no schema das sessões de chat e um processo de cleanup para remover arquivos de sessão expirados.
2. **Adotar Cookies Seguros**: Migrar a gestão de sessão (especialmente para autenticação futura) para cookies com as flags `HttpOnly`, `Secure` e `SameSite=Strict`.
3. **Invalidação de Sessão**: Implementar um endpoint de "logout" ou encerramento de sessão que invalide o `session_id` no servidor.
4. **Restringir CORS**: Alterar a configuração de CORS para permitir apenas origens confiáveis, especialmente se `allow_credentials` for mantido como `True`.

---
Auditoria realizada por: gemini-cli
Data: 2026-03-07
Status da Task: complete
