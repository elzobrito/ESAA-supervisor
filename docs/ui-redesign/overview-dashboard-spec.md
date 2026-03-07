# UIR-SPEC-003: Visao Geral Executiva

## Objetivo
Transformar a entrada principal do ESAA Supervisor em uma tela executiva de leitura rapida, capaz de responder em poucos segundos:
- qual o estado geral do projeto
- o que esta bloqueado
- qual a proxima tarefa elegivel
- se a integridade do projeto exige atencao imediata

## Papel da Tela
A Visao Geral substitui a pagina longa atual como landing page do projeto. Ela nao tenta ser uma tela de trabalho detalhado; seu papel e sintetizar estado, destacar anomalias e apontar proximos passos.

## Estrutura de Layout
- faixa superior com titulo do projeto, seletor de projeto e status global de integridade
- primeira linha de KPIs com 4 a 6 cards
- segunda linha com 2 graficos operacionais principais
- terceira linha com cards de proxima tarefa elegivel, problemas em aberto e atividade recente resumida
- area secundaria com resumos curtos de runners, ultimas runs e artefatos com falha de integridade quando houver

## KPIs Obrigatorios
- `Tasks Done`: total de tarefas concluidas
- `Tasks Em Andamento`: quantidade atual em `in_progress`
- `Tasks Bloqueadas`: tarefas `todo` inelegiveis por dependencia ou issue aberta
- `Open Issues`: quantidade de issues abertas
- `Health`: estado consolidado de integridade (`ok`, `warn`, `mismatch`)
- `Current Run`: status da run ativa, se existir

## Regras dos Cards KPI
- cada card deve combinar numero principal, rotulo, delta ou contexto curto
- cards criticos usam cor semaforica apenas como acento, sem depender so de cor para significado
- ao clicar em um KPI, a interface deve levar para a tela operacional correspondente ou aplicar filtro contextual

## Paineis Resumidos Obrigatorios
- `Proxima Tarefa Elegivel`
  - exibe task_id, titulo, kind, agente preferencial e CTA para abrir em tarefas/execucao
- `Problemas em Aberto`
  - mostra as 3 a 5 issues mais relevantes por severidade e recencia
- `Atividade Recente`
  - mostra de 5 a 8 eventos recentes com tipo, actor, task e horario

## Integridade em Destaque
- a tela deve exibir um bloco de integridade visivel sem ocupar o centro inteiro
- quando `verify_status != ok`, o bloco sobe de prioridade visual e oferece CTA para abrir tela de integridade/atividade
- mismatch de hash, parse error e schema error devem ter linguagem distinta

## Estados da Tela
- `loading`: skeletons para KPIs, charts e cards
- `empty`: projeto sem dados relevantes, com explicacao curta e CTA para carregar projeto/rodar primeira acao
- `nominal`: dados consolidados carregados
- `attention`: existe issue critica, run com erro ou integridade inconsistente

## Navegacao e Acoes
- clique em KPI abre tela filtrada relacionada
- clique em proxima tarefa elegivel abre drawer da task ou tela de tarefas
- clique em problema abre detalhe contextual
- clique em atividade abre timeline completa com payload

## Requisitos de UX
- nenhuma secao critica deve exigir scroll para aparecer em desktop comum
- a tela deve permitir leitura em Z: KPIs, charts, proximos passos
- informacao detalhada fica em telas dedicadas, nao em listas extensas na home
