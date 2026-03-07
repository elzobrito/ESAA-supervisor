# UIR-SPEC-003: Charts e KPIs Operacionais

## Objetivo
Definir os graficos e indicadores que sustentam a Visao Geral sem cair em visualizacao decorativa.

## Graficos Obrigatorios
- `Distribuicao por Status`
  - tipo recomendado: donut ou barras horizontais
  - mostra `todo`, `in_progress`, `review`, `done`
  - uso principal: saude do fluxo de entrega
- `Fluxo de Atividade no Tempo`
  - tipo recomendado: barras por janela temporal ou linha discreta
  - mostra volume de eventos por janela curta
  - uso principal: identificar projeto parado, pico de atividade ou comportamento anomalo

## Graficos Secundarios Permitidos
- `Tasks por Kind`
- `Carga por Runner`
- `Issues por Severidade`

## Regras de Utilidade
- todo grafico deve responder uma pergunta operacional explicita
- valores absolutos e rotulos devem ficar visiveis sem hover obrigatorio
- palette deve ser coerente com status operacionais do sistema

## Definicao dos KPIs
- `Done Rate`
  - percentual de tarefas done sobre total
- `Blocked Queue`
  - total de tarefas sem elegibilidade
- `Issue Pressure`
  - total ponderado por severidade
- `Run Health`
  - combina status da run atual e ultimo erro conhecido

## Tratamento de Dados
- ausencia de dados deve virar estado vazio explicito
- dados inconsistentes devem exibir badge `dados incompletos`
- graficos nao devem quebrar quando houver apenas uma categoria presente

## Comportamento Responsivo
- em desktop, dois graficos lado a lado
- em largura media, um por linha
- em viewport pequena, cards KPI continuam acima e charts descem na ordem de importancia

## Verificacao Esperada
- existem ao menos 4 KPI cards principais
- existem ao menos 2 graficos operacionais uteis
- a pagina resume proxima tarefa, problemas e atividade recente sem scroll excessivo
