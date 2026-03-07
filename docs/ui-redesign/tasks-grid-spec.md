# UIR-SPEC-004: Tela de Tarefas com Grid

## Objetivo
Transformar tarefas na principal superficie operacional de inspeção e decisao, com densidade alta de informacao e baixo custo de navegacao.

## Estrutura da Tela
- cabecalho com titulo, contadores resumidos e ultima atualizacao
- barra fixa de filtros e busca
- data grid central
- drawer lateral para detalhe contextual da task

## Colunas Minimas da Grid
- `task_id`
- `title`
- `task_kind`
- `status`
- `assigned_to`
- `preferred_runner`
- `eligibility`
- `updated_at` ou melhor proxy temporal disponivel
- `actions`

## Filtros Obrigatorios
- por `status`
- por `task_kind`
- por `runner preferencial`
- por `elegibilidade`
- busca textual por `task_id`, `title` e `assigned_to`

## Ordenacao
- por default, tarefas em andamento e review aparecem antes
- permitir ordenacao por `task_id`, `status`, `kind` e recencia

## Regras de Badge e Densidade
- status usa badge semantica consistente com o sistema visual
- elegibilidade deve ficar visivel na linha, nao escondida apenas no detalhe
- dependencia bloqueante pode aparecer como hint curto na linha

## Acoes por Linha
- abrir detalhe
- executar task, quando elegivel
- abrir atividade relacionada
- abrir artefatos/outputs, quando disponiveis

## Estados
- `loading`: linhas skeleton
- `empty`: nenhuma tarefa
- `no_results`: filtros sem resultado
- `attention`: existem tarefas bloqueadas por issue critica

## Regras de UX
- grid deve suportar leitura rapida sem perder contexto
- filtros nao podem empurrar a tabela para baixo em excesso
- detalhe da tarefa nao deve exigir navegar para outra rota principal
