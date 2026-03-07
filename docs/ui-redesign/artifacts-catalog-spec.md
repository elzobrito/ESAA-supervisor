# UIR-SPEC-005: Catalogo de Artefatos Canonicos

## Objetivo
Mover a inspeção detalhada dos artefatos para uma experiencia dedicada, tirando esse peso da tela principal.

## Papel da Tela
- inventario canônico do projeto
- auditoria de integridade
- descoberta de origem, papel e relacionamento de artefatos

## Estrutura
- header com contadores de integridade
- filtros por categoria, role, status de integridade e origem
- tabela/catalogo central
- drawer de detalhe do artefato

## Colunas Minimas
- nome
- path
- category
- role
- integrity_status
- last_modified
- size

## Filtros Obrigatorios
- category
- integrity_status
- role
- busca textual por nome/path

## Detalhe do Artefato
- metadados principais
- origem no sistema
- relacao com roadmap/plugin quando aplicavel
- resumo de integridade
- links para visualizacao de conteudo ou contexto relacionado

## Regras de UX
- a home passa a mostrar apenas resumo de integridade e atalhos para o catalogo
- o catalogo suporta inspecao profunda sem invadir a area central da dashboard executiva
