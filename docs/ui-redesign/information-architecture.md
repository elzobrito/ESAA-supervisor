# UIR-SPEC-001: Arquitetura da Informacao

## Objetivo
Reorganizar o ESAA Supervisor em uma arquitetura baseada em telas claras, reduzindo scroll excessivo e separando leitura executiva, operacao e auditoria.

## Principios
- uma tela principal para cada intencao dominante
- baixa competicao visual entre blocos
- detalhes profundos em drawers, modais ou telas dedicadas
- navegacao previsivel e persistente

## Secoes Principais
- `Visao Geral`
  - leitura executiva, KPIs, graficos e proximos passos
- `Tarefas`
  - grid operacional, filtros e drawer de detalhe
- `Execucao`
  - runs, console dock, historico e estado atual
- `Atividade`
  - timeline detalhada de eventos com payload
- `Artefatos`
  - catalogo dedicado de artefatos canônicos
- `Integridade`
  - estado de verificacao, inconsistencias e problemas estruturais
- `Issues`
  - problemas em aberto com contexto e impacto
- `Lessons`
  - licoes aprendidas com detalhe operacional
- `Configuracao`
  - preferencias locais, runner padrao e parametros de UX

## Modelo de Navegacao
- app shell persistente com topbar + sidebar esquerda
- navegação primaria na sidebar
- acoes contextuais e filtros no header da tela
- overlays para inspeção sem perda de contexto

## Relacoes Entre Telas
- `Visao Geral` aponta para `Tarefas`, `Issues`, `Atividade` e `Integridade`
- `Tarefas` abre detalhe lateral e pode disparar `Execucao`
- `Execucao` se conecta com `Atividade` e `Artefatos`
- `Artefatos` e `Integridade` formam o eixo de auditoria

## Regras de Prioridade
- home longa atual deve ser substituida por telas especializadas
- a informacao critica sobe para Visao Geral
- inventario detalhado e logs completos saem da landing page

## Breadcrumbs e Contexto
- cada tela deve exibir titulo, contexto do projeto e acoes principais
- detalhes em drawer preservam contexto da tela base
- o usuario nunca deve se perder entre auditoria e operacao
