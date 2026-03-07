# ESUP-SPEC-004: Política de Roteamento e Execução de Agentes

## 1. Roteamento de Agentes (Agent Routing)
O supervisor deve ser capaz de escolher o melhor agente para cada tarefa com base no `task_kind` ou configurações do projeto.

### 1.1. Critérios de Escolha (Exemplo POC)
- **`task_kind: spec`:** Preferir `claude-code` ou `gemini-cli` (forte raciocínio e conformidade com especificações).
- **`task_kind: impl`:** Preferir `claude-code` ou `codex` (forte capacidade de geração de código e refatoração).
- **`task_kind: qa`:** Preferir `gemini-cli` ou `claude-code` (forte capacidade de verificação e escrita de testes).

### 1.2. Prioridade e Substituição (Fallback)
1. **Configuração Explícita:** Se o roadmap especificar um `assigned_to: agent-id`, o supervisor deve usar o adapter correspondente.
2. **Prioridade Global:** Se não houver atribuição, o roteador segue uma lista de prioridades definida no `init.yaml` ou `agents_swarm.yaml`.
3. **Fallback Automático:** Se o agente preferencial falhar (ex: erro de autenticação), o roteador pode tentar o próximo agente da lista (se permitido pela política).

## 2. Política de Execução Supervisionada

### 2.1. Estágio: Preflight (Pré-execução)
- Verificação de ambiente: O supervisor checa se a CLI do agente está disponível no `PATH`.
- Injeção de Contexto: Preparação do `TaskContext` a partir do `roadmap.json` e arquivos reais.
- Prompt Inicial: O supervisor anexa o conteúdo de `init.yaml` e as `active_lessons` ao prompt enviado ao agente.

### 2.2. Estágio: Execução (Execution)
- O runtime invoca o adapter em um thread/subprocesso separado.
- Streaming de logs é iniciado imediatamente para o frontend.
- O supervisor monitora o uso de recursos e tempo limite (TTL).

### 2.3. Estágio: Pós-execução (Post-execution)
- O supervisor recebe o `AgentResult` do adapter.
- Se `AgentResult.action == complete`, o supervisor dispara a validação estrutural (`Workflow Gates`) antes de persistir o evento no `activity.jsonl`.
- Se a validação falhar, o supervisor pode emitir um `issue.report` e não reprojetar o estado como `done`.

## 3. Autoridade vs. Cognição
- **Cognição (Agente):** Responsável por entender a tarefa, ler arquivos, propor mudanças de código e gerar o evento de conclusão.
- **Autoridade (Runtime):** Responsável por injetar o contexto correto, garantir o fluxo canônico (não permitir `complete` sem `claim`), validar as saídas, persistir os eventos e atualizar as projeções (roadmap).

## 4. Configuração de Agentes
- Os parâmetros de cada agente (API keys, modelos, flags extras) devem ser configurados via variáveis de ambiente (`.env`) ou via interface web do supervisor.
