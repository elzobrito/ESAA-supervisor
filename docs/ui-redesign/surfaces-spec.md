# UIR-SPEC-005: Superficies Complementares

## Objetivo
Definir padroes reutilizaveis para superfícies auxiliares da nova UI, reduzindo poluicao na tela principal e melhorando inspeção contextual.

## Tipos de Superficie
- `Modal`
  - para payload tecnico, confirmacoes e leitura focada
- `Drawer`
  - para detalhe contextual sem perder a tela base
- `Console Dock`
  - para execucao ao vivo e observabilidade persistente

## Regras de Uso
- usar modal quando a tarefa exigir foco temporario ou comparacao curta
- usar drawer quando o usuario precisar manter contexto da tela base
- usar dock para experiencia de execucao transversal e persistente entre rotas operacionais

## Conteudos Recomendados para Modal
- payload bruto de evento
- detalhe de integridade
- confirmacao de acao destrutiva ou sensivel

## Conteudos Recomendados para Drawer
- detalhe de task
- detalhe de issue
- detalhe de lesson
- detalhe resumido de artefato

## Dock de Execucao
- fixo na base
- recolhivel e expansivel
- persistente durante a run
- pode acompanhar o usuario entre overview, tasks e activity

## Comportamento Global
- overlays nao devem competir entre si
- a aplicacao deve impedir drawer e modal conflitantes sem hierarquia clara
- foco, esc e fechamento devem seguir regras consistentes
