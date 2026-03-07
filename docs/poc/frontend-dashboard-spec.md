# ESUP-SPEC-003: Especificação do Dashboard do Frontend (React)

## 1. Visão Geral
O frontend do Supervisor ESAA Web é uma Single Page Application (SPA) construída com React e Vite, focada em fornecer uma interface clara para a supervisão de roadmaps e execução de agentes.

## 2. Arquitetura de Componentes

### 2.1. Layout Base
- **Sidebar:** Navegação entre a lista de projetos e configurações globais.
- **Header:** Exibe o nome do projeto aberto, status de integridade (OK/Mismatch) e ações rápidas (Refresh).
- **Main Content:** Área dinâmica para renderização das páginas (Dashboard, Projects).

### 2.2. Componentes do Dashboard
- **ArtifactsPanel:** Lista lateral ou superior exibindo os artefatos canônicos encontrados em `.roadmap/` (activity, issues, lessons, etc.) com badges de status de parse/validação.
- **TasksTable:** Tabela principal com as tarefas do roadmap.
  - **Filtros:** Por status (`todo`, `in_progress`, `review`, `done`) e por kind (`spec`, `impl`, `qa`).
  - **Busca:** Campo de texto para filtrar por título ou ID.
- **TaskDetails (Modal/Drawer):** Exibe a descrição completa, dependências, alvos (`targets`), saídas esperadas (`outputs`) e evidências de verificação se concluída.
- **ActivityPanel:** Timeline de eventos lidos do `activity.jsonl`.
- **Issues/Lessons Panels:** Listas compactas de problemas abertos e lições aprendidas no projeto.

## 3. Console de Execução (RunConsole)
Componente crítico para acompanhar o ciclo supervisionado em tempo real.
- **Status da Run:** Badge indicando a fase atual (Claiming, Technical Execution, Syncing).
- **Log Monitor:** Área de texto com auto-scroll exibindo `stdout/stderr` do agente.
- **Controles:** Botão "Run Next Task" (seleção automática) ou "Run Task" (seleção manual) e botão "Cancel Run".

## 4. Contratos Visuais e Estilização
- **Estilo:** Moderno, limpo, utilizando Vanilla CSS ou uma biblioteca minimalista de UI.
- **Feedback Visual:**
  - `in_progress`: Animação de pulso ou spinner.
  - `review`: Destaque para ação pendente do usuário.
  - `done`: Checkmark verde com imutabilidade visual.
  - `error`: Cor de alerta com link para o `IssuesPanel`.

## 5. Fluxo de Interação
1. O usuário abre o dashboard do projeto.
2. O frontend consome `/state` para popular os painéis.
3. O usuário clica em "Run Next Task".
4. O frontend abre o `RunConsole` e conecta ao `/logs/stream`.
5. Ao término (evento `run_end`), o frontend dispara um re-fetch do `/state` para atualizar a UI.
