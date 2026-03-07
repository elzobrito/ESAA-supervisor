# UIR-SPEC-002: App Shell

## Objetivo
Definir um shell de aplicação persistente, denso e elegante, com maior controle de foco visual e navegacao.

## Estrutura
- topbar fixa
- sidebar esquerda colapsável
- area principal de conteudo
- area opcional para dock inferior de execucao

## Topbar
- titulo da secao atual
- contexto do projeto
- acoes globais
- atalho para busca, refresh e configuracoes

## Sidebar
- modo expandido com label + icone
- modo colapsado com icone + tooltip
- grupo principal e grupo secundario
- CTA de recolher/expandir sempre visivel

## Estados do Shell
- `expanded`
- `collapsed`
- `mobile-overlay`

## Persistencia
- preferencia do usuario salva localmente
- estado reaplicado ao navegar entre telas
- em viewport pequena, o shell pode forcar comportamento overlay

## Regras de Espaco
- recolher sidebar deve ampliar area util do conteudo
- a largura principal deve privilegiar overview, tasks e activity
- console dock nao pode quebrar o grid principal
