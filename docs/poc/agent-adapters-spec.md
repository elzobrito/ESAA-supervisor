# ESUP-SPEC-004: Especificação de Adapters de Agentes

## 1. Visão Geral
Os adapters isolam a lógica de invocação de agentes externos (CLI), normalizando a entrada (`TaskContext`) e a saída (`AgentResult`). Cada agente é executado como um subprocesso supervisionado pelo runtime.

## 2. Contratos Internos

### 2.1. TaskContext
Objeto injetado no adapter para fornecer o contexto da tarefa.
```json
{
  "task_id": "string",
  "task_kind": "spec | impl | qa",
  "description": "string",
  "targets": ["path/to/dir/or/file"],
  "outputs": { "files": ["path/to/output"] },
  "prior_status": "todo | in_progress",
  "active_lessons": [ { "id": "L-001", "content": "..." } ]
}
```

### 2.2. AgentResult (Proposta de Trabalho)
Estrutura única retornada por qualquer adapter após a execução do agente.
```json
{
  "action": "claim | complete | issue.report",
  "actor": "agent-id",
  "payload": {
    "task_id": "string",
    "verification_checks": [ { "id": "string", "status": "pass | fail" } ],
    "file_updates": [ { "path": "string", "content": "string" } ]
  },
  "metadata": {
    "exit_code": 0,
    "duration_ms": 1200,
    "raw_output": "stdout/stderr content"
  }
}
```

## 3. Implementação dos Adapters

### 3.1. Subprocessos e Captura
- **Invocação:** O adapter utiliza `subprocess.Popen` (Python) para rodar o comando CLI do agente (ex: `gemini "..."`, `claude "..."`).
- **Streaming:** O `stdout` e `stderr` são capturados linha a linha e encaminhados para o buffer de logs do runtime em tempo real.
- **Timeout:** Cada adapter deve respeitar um tempo limite configurável (default: 10 min para POC).

### 3.2. Normalização de Saída
O adapter é responsável por:
1. Extrair o JSON de evento da saída do agente (procurando por blocos demarcados ou última linha válida).
2. Validar se o evento segue o esquema `AgentResult`.
3. Converter falhas de execução (exit code != 0) em eventos do tipo `issue.report`.

## 4. Tratamento de Falhas e Cancelamento
- **Cancelamento:** Ao receber sinal de cancelamento da API, o runtime sinaliza o adapter, que deve enviar um `SIGTERM/SIGKILL` ao subprocesso do agente.
- **Falha Crítica:** Se o agente não retornar um JSON válido após o trabalho, o adapter gera um `AgentResult` com `action: issue.report` detalhando o erro de parse.
