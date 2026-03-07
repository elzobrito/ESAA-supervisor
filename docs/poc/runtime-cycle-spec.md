# ESUP-SPEC-002: Especificação do Ciclo de Runtime do Supervisor

## 1. Visão Geral
O runtime do Supervisor ESAA Web é responsável por coordenar a execução de tarefas, garantindo a integridade do fluxo canônico (`claim -> complete -> review`) e a auditabilidade através do `activity.jsonl`.

## 2. Ciclo de Vida da Sessão

### 2.1. Bootstrap do Projeto
1. **Localização:** O supervisor identifica a pasta `.roadmap/` no diretório raiz do projeto aberto.
2. **Descoberta (Discovery):** Varredura de artefatos canônicos (`roadmap.json`, `activity.jsonl`, `issues.json`, `lessons.json`, `*.yaml`).
3. **Validação Estrutural:** Verificação de integridade e parse inicial (JSON/YAML/JSONL).
4. **Projeção Inicial:** Replay de eventos do `activity.jsonl` para garantir que as visualizações (Read Models) estão sincronizadas com a fonte da verdade.

### 2.2. Loop de Execução Supervisionada
Para cada execução de tarefa (Run):

1. **Seleção e Elegibilidade:**
   - O runtime identifica a próxima tarefa `todo` sem dependências pendentes.
   - Verifica se há bloqueios (`issues` abertos) que impeçam a tarefa.
   - Aplica filtros de escopo/lote se configurados.

2. **Invocação 1: Claim (Passo Obrigatório)**
   - **Contexto:** Injeta `task_id`, `task_kind`, `task_description` e `active_lessons`.
   - **Execução:** Invoca o agente configurado (Gemini CLI, Claude Code ou Codex).
   - **Output:** O agente deve emitir um `activity_event` com `action: claim`.
   - **Validação:** O runtime aplica o `WG-001` (Claim antes do trabalho).
   - **Persistência:** O evento `claim` é anexado ao `activity.jsonl`.
   - **Reprojeção:** O status da tarefa no `roadmap.json` muda para `in_progress`.

3. **Invocação 2: Execução Técnica e Complete**
   - **Contexto:** Injeta o estado atual dos arquivos relevantes (`prior_file_state`) e confirma status `in_progress`.
   - **Execução:** O agente realiza o trabalho técnico (spec, impl ou qa).
   - **Output:** O agente deve emitir `action: complete` junto com `file_updates` e `verification.checks`.
   - **Validação:**
     - `WG-002`: Verifica se há `verification.checks` mínimos.
     - `WG-004`: Verifica se o ator é o mesmo que fez o `claim`.
     - `WG-005`: Verifica se não houve colapso de ações.
   - **Persistência:** O evento `complete` e as atualizações de arquivos são processados.
   - **Reprojeção:** O status da tarefa no `roadmap.json` muda para `review`.

4. **Finalização e Review**
   - O runtime atualiza a interface web com o resultado.
   - O sistema aguarda o evento de `review` (que pode ser automático via QA ou manual via interface).

## 3. Estados Operacionais do Runtime
- **IDLE:** Aguardando comando ou monitorando mudanças em arquivos.
- **PREFLIGHT:** Validando ambiente e elegibilidade antes de iniciar run.
- **RUNNING:** Agente externo em execução (subprocesso ativo).
- **SYNCING:** Escrevendo eventos e atualizando projeções.
- **CANCELLING:** Encerrando subprocesso e limpando locks temporários.
- **ERROR:** Estado de falha crítica que exige intervenção manual ou reset.

## 4. Gestão de Logs e Observabilidade
- **Captura:** O runtime captura `stdout` e `stderr` do agente em tempo real.
- **Streaming:** Encaminha os logs para o frontend via Server-Sent Events (SSE).
- **Persistência:** Logs de execução podem ser armazenados temporariamente em memória para consulta durante a run e descartados ou movidos para histórico após `run.end`.

## 5. Lock e Concorrência
- **Lock por Projeto:** Apenas uma run ativa por diretório `.roadmap/`.
- **Lock por Tarefa:** O campo `assigned_to` no roadmap impede que múltiplos agentes trabalhem na mesma tarefa simultaneamente.
