# Auditoria de Logs e Monitoramento - SEC-020

## Resumo Executivo
A auditoria do domínio de **Logs e Monitoramento** no sistema **ESAA-supervisor (PoC)** revelou uma implementação robusta de auditoria de estado (event sourcing), mas falhas críticas na proteção de dados sensíveis e na observabilidade proativa. O risco mais imediato é a exposição de segredos através do streaming de logs de agentes (stdout/stderr), que não passa por nenhuma camada de sanitização antes de ser transmitido via SSE (Server-Sent Events). Além disso, a ausência de alertas de segurança e de correlação de requisições dificulta a resposta a incidentes e a rastreabilidade em escala.

## Detalhes dos Checks (Playbook LM-001 a LM-005)

| ID | Check | Status | Severidade | Evidência/Observação |
| --- | --- | --- | --- | --- |
| LM-001 | Logs com dados sensíveis | **FAIL** | **CRITICAL** | `LogStreamer` e `routes_logs.py` transmitem stdout/stderr bruto dos agentes sem redação. |
| LM-002 | Logs de auditoria | **PASS** | - | `EventWriter` garante trilha completa de mutações no `activity.jsonl`. |
| LM-003 | Logs não estruturados | **PASS** | - | Uso consistente de JSONL para atividade e Pydantic para logs de execução. |
| LM-004 | Alertas de segurança | **FAIL** | MEDIUM | Ausência de integração com Sentry, Slack ou mecanismos de notificação de erros/anomalias. |
| LM-005 | Correlação de requisições | **FAIL** | LOW | Ausência de Correlation ID middleware para rastrear requests entre API e sub-processos. |

## Análise de Risco

### 1. Vazamento de Credenciais em Tempo Real (LM-001)
Como os agentes LLM (Codex, Gemini, Claude) operam frequentemente com chaves de API e segredos em seu contexto ou saída técnica, a falta de um filtro de redação (redaction filter) no `LogStreamer` permite que qualquer pessoa com acesso à rede do supervisor visualize segredos em texto plano através do dashboard ou do endpoint SSE.

### 2. Audit Trail de Estado vs. Audit Trail de Acesso (LM-002)
O sistema brilha na auditoria de mudanças de estado (quem mudou qual tarefa e quando). No entanto, não há log de auditoria de *leitura* (quem visualizou quais artefatos ou roadmaps), o que é uma lacuna importante considerando que o sistema permite navegar em arquivos do host.

### 3. Silêncio Operacional (LM-004)
Falhas críticas de integridade (ex: alteração manual de um `activity.jsonl` invalidando o hash de projeção) são detectadas silenciosamente. O operador só percebe o problema ao abrir manualmente o dashboard e ver o status de integridade, sem qualquer push notification ou alerta externo.

## Recomendações

1. **Implementar Redaction Filter**: Adicionar um middleware no `LogStreamer` que utilize regex para detectar e mascarar padrões de chaves de API (ex: `sk-...`, `AIza...`), tokens e senhas antes do streaming e persistência em memória.
2. **Correlation ID**: Adicionar middleware ao FastAPI para gerar um `X-Request-ID` em cada requisição, injetando-o no contexto de log para permitir o rastreio fim-a-fim de uma ação do usuário até a execução do agente.
3. **Mecanismo de Alerta**: Integrar um hook simples (ex: `SecurityAlertService`) que possa disparar webhooks ou logs de nível `CRITICAL` quando falhas de integridade forem detectadas pelo `ArtifactValidator`.
4. **Auth no Stream de Logs**: Proteger o endpoint `/api/v1/projects/{id}/logs/stream/{run_id}` com autenticação, impedindo o acesso anônimo a saídas de console potencialmente sensíveis.

---
Auditoria realizada por: gemini-cli
Data: 2026-03-07
Status da Task: complete
