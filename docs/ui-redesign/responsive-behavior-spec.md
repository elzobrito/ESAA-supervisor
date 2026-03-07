# UIR-SPEC-002: Comportamento Responsivo

## Objetivo
Manter o shell operacional e legivel em desktop, notebook e viewport menor sem sacrificar o foco do conteudo.

## Desktop
- sidebar pode ficar expandida ou colapsada
- topbar fixa
- drawers abrem lateralmente
- charts e grids podem ocupar duas colunas

## Largura Media
- sidebar prioriza modo colapsado
- cards e charts podem empilhar
- filtros da tela de tarefas podem quebrar em mais linhas

## Mobile ou Janela Pequena
- sidebar vira overlay temporario
- drawer pode ocupar tela inteira
- topbar concentra navegacao e toggle
- prioridade para leitura e acao principal, nao para densidade maxima

## Regras
- nenhum CTA principal pode ficar escondido fora da viewport sem alternativa
- o usuario deve conseguir abrir/fechar menu sempre
- o colapso do menu precisa gerar ganho real de area util no desktop

## Verificacao Esperada
- modo expandido e colapsado especificados
- ganho de largura do conteudo definido
- comportamento consistente em desktop e tela reduzida
