# UIR-SPEC-005: Console Dock de Execucao

## Objetivo
Criar uma experiencia de observabilidade operacional forte, sem transformar a pagina principal em um terminal permanente.

## Estrutura do Dock
- header com task atual, runner, status da run e controles principais
- timeline curta das etapas da run
- painel de logs ao vivo com filtros de origem
- atalhos para abrir tela completa de runs e artefatos tocados

## Estados
- recolhido
- semiaberto
- expandido
- erro
- concluido

## Regras de Comportamento
- permanece acessivel enquanto existe run ativa
- pode continuar visivel apos a run para leitura de pos-execucao
- nao deve cobrir CTAs principais de forma destrutiva
- deve suportar scroll proprio e auto-scroll opcional nos logs

## Conteudo Obrigatorio
- status atual
- task corrente
- runner atual
- logs em tempo real
- passos do ciclo supervisor
- artefatos tocados, quando conhecidos

## Integracao com a UX
- overview mostra estado resumido da run e CTA para abrir dock
- tela de tasks pode disparar execucao e manter o usuario no contexto
- timeline de atividade pode apontar para a run correspondente

## Verificacao Esperada
- especificacao cobre modais, drawers e dock inferior
- artefatos saem do centro da home e ganham catalogo proprio
- console de execucao fica acoplado a experiencia operacional
