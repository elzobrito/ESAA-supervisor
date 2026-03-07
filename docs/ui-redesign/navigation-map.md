# UIR-SPEC-001: Mapa de Navegacao

## Rotas Principais
- `/projects`
  - lista de projetos
- `/dashboard/:projectId/overview`
  - visao geral executiva
- `/dashboard/:projectId/tasks`
  - tarefas
- `/dashboard/:projectId/runs`
  - execucao e runs
- `/dashboard/:projectId/activity`
  - timeline de atividade
- `/dashboard/:projectId/artifacts`
  - catalogo de artefatos
- `/dashboard/:projectId/integrity`
  - integridade e verificacoes
- `/dashboard/:projectId/issues`
  - issues abertas e historico
- `/dashboard/:projectId/lessons`
  - lessons ativas e consulta
- `/dashboard/:projectId/settings`
  - configuracoes e preferencias locais

## Navegacao Primaria
- overview
- tasks
- runs
- activity
- artifacts

## Navegacao Secundaria
- integrity
- issues
- lessons
- settings

## Regras da Sidebar
- expansivel e colapsavel
- labels visiveis no modo expandido
- apenas icones + tooltip no modo colapsado
- item ativo sempre destacado

## Fluxos Criticos
- abrir projeto -> overview
- ver proxima task -> tasks drawer
- disparar execucao -> runs ou dock
- investigar erro -> issues ou integrity
- inspecionar evento -> activity modal/drawer

## Verificacao Esperada
- rotas e seções operacionais definidas
- substituição da home longa por arquitetura baseada em telas
- sidebar colapsável prevista como eixo da navegação
