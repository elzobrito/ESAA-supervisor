# UIR-SPEC-004: Drawer de Detalhe da Task

## Objetivo
Permitir inspeção aprofundada de uma task sem remover o usuario da tela de tarefas.

## Abertura
- abre a partir da linha da grid
- ocupa lateral direita em desktop
- em telas menores, pode virar full-height sheet

## Conteudo Obrigatorio
- cabecalho com `task_id`, titulo, status e kind
- descricao completa
- dependencias
- elegibilidade atual com motivos de bloqueio, se houver
- `assigned_to`, `preferred_runner` e hints de roteamento
- outputs esperados e outputs ja produzidos
- eventos recentes ligados a task
- area de acoes contextuais

## Organizacao Interna
- secoes ou abas:
  - `Resumo`
  - `Dependencias e Elegibilidade`
  - `Atividade`
  - `Outputs`

## Acoes no Drawer
- executar task
- abrir timeline filtrada
- abrir artefatos relacionados
- copiar identificadores tecnicos

## Regras de Comportamento
- fechar drawer nao perde scroll nem filtros da grid
- abrir outra task substitui o conteudo do drawer, sem recarregar a tela inteira
- o drawer deve aceitar estados `loading` e `error`

## Verificacao Esperada
- colunas e filtros da grid estao definidos
- drawer lateral cobre detalhes, dependencias e outputs
- a experiencia evita navegacao longa para inspecao de task
