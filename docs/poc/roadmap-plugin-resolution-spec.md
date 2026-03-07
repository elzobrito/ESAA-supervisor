# ESAA Supervisor PoC - Especificacao de Resolucao do Roadmap Ativo

## Objetivo

Definir como o supervisor seleciona o `roadmap` ativo para operacao quando existem multiplos arquivos `roadmap*.json` e `roadmap*.schema.json`, incluindo candidatos da raiz e candidatos historicos em `snapshots/`.

## Escopo

Esta especificacao cobre:

- identificacao de candidatos de roadmap
- associacao entre roadmap e schema
- derivacao de `plugin_id`
- selecao do plugin ativo
- definicao de modo operacional: `read_write`, `read_only` ou `blocked`
- razoes de inelegibilidade que devem aparecer na API e na UI

Fica fora de escopo:

- calculo da proxima task elegivel
- execucao de agentes
- logica de review

## Definicoes

- `roadmap candidate`: qualquer arquivo que case com `roadmap*.json`
- `schema candidate`: qualquer arquivo que case com `roadmap*.schema.json`
- `plugin`: bundle logico composto por um roadmap e, quando possivel, por um schema associado
- `active plugin`: plugin selecionado para leitura e, se saudavel, para operacao mutavel
- `snapshot plugin`: plugin descoberto sob `.roadmap/snapshots/**`

## Derivacao de plugin_id

As regras de derivacao devem ser deterministicas:

- `roadmap.json` -> `plugin_id=default`
- `roadmap.<nome>.json` -> `plugin_id=<nome>`
- `roadmap-<nome>.json` -> `plugin_id=<nome>`
- `roadmap_<nome>.json` -> `plugin_id=<nome>`
- candidatos em snapshot devem prefixar o snapshot: `snapshot/<snapshot_name>/<plugin_id>`

Se dois candidatos produzirem o mesmo `plugin_id` no mesmo escopo, ambos devem ser marcados com colisao e o sistema nao pode escolher nenhum deles automaticamente.

## Associacao entre roadmap e schema

Para cada roadmap candidate, o supervisor deve resolver schema nesta ordem:

1. schema irmao com o mesmo sufixo do roadmap
2. `roadmap.schema.json` na raiz `.roadmap/`
3. nenhum schema encontrado

Exemplos:

- `roadmap.json` usa `roadmap.schema.json`
- `roadmap.web.json` prefere `roadmap.web.schema.json`; se nao existir, cai para `roadmap.schema.json`

Se nenhum schema aplicavel for encontrado, o candidato continua visivel, mas com `schema_status=missing` e `operational_mode=read_only`.

## Contrato de Candidato

Cada candidato deve expor:

- `plugin_id`
- `roadmap_path`
- `schema_path`
- `scope`
- `parse_status`
- `schema_status`
- `integrity_status`
- `verify_status`
- `operational_mode`
- `selection_reason`
- `blocking_reasons`

## Regras de Saude

### Parse

- JSON invalido -> `parse_status=error`, `operational_mode=blocked`

### Schema

- schema invalido ou roadmap fora do schema -> `schema_status=error`, `operational_mode=blocked`
- schema ausente -> `schema_status=missing`, `operational_mode=read_only`

### Integridade operacional

O candidato so pode operar em modo `read_write` quando todas as condicoes abaixo forem verdadeiras:

- `parse_status=ok`
- `schema_status=ok`
- `scope=root`
- `integrity_status=ok`
- `verify_status=ok` ou equivalente saudavel

O candidato deve cair para `read_only` quando:

- estiver em `snapshot`
- nao houver schema aplicavel
- `verify_status=unknown` ou `mismatch`
- houver warning nao bloqueante que permita apenas inspecao

O candidato deve ficar `blocked` quando:

- parse falhar
- validacao de schema falhar
- houver colisao de `plugin_id`
- `verify_status=corrupted`
- o roadmap estiver estruturalmente incompleto

## Algoritmo de Resolucao do Plugin Ativo

O algoritmo deve seguir exatamente esta ordem:

1. Se o usuario ou a API informar `plugin_id` explicito, tentar esse candidato primeiro.
2. Se o candidato explicito nao existir, retornar erro deterministico.
3. Se o candidato explicito existir mas estiver `blocked`, abrir o projeto em modo de inspecao e reportar o bloqueio; nao permitir `claim`, `complete` ou `review`.
4. Sem selecao explicita, preferir `plugin_id=default` no escopo `root`.
5. Se o default nao existir, escolher o primeiro candidato `root` com `operational_mode=read_write`, ordenado por `plugin_id`.
6. Se nao existir candidato `read_write`, escolher o primeiro `root` em `read_only`, ordenado por `plugin_id`, e abrir o projeto degradado.
7. Nunca selecionar automaticamente plugins de `snapshot`; eles exigem opt-in explicito.

## Estados Expostos para UI e API

O backend deve retornar:

- `active_plugin`
- `candidates`
- `selection_mode`: `explicit`, `default_fallback`, `root_fallback`, `degraded`, `snapshot_explicit`
- `write_capability`: `enabled` ou `disabled`

Cada candidato deve expor razoes claras de inelegibilidade, por exemplo:

- `missing_schema`
- `schema_validation_failed`
- `verify_status_mismatch`
- `verify_status_corrupted`
- `snapshot_scope_requires_opt_in`
- `plugin_id_collision`

## Exemplo Aplicado a Este Projeto

No estado atual da PoC, o discovery encontra pelo menos:

- `.roadmap/roadmap.json` -> `plugin_id=default`, escopo `root`
- `.roadmap/roadmap.schema.json` -> schema default
- `.roadmap/snapshots/legacy_20260227/roadmap.json` -> `plugin_id=snapshot/legacy_20260227/default`

Pela regra desta especificacao:

- o plugin default da raiz e o unico candidato elegivel para operacao normal
- o snapshot legado permanece visivel para auditoria, mas nao pode ser selecionado automaticamente

## Requisitos

1. O supervisor deve identificar o roadmap ativo sem assumir unicidade de `roadmap.json`.
2. O supervisor deve associar cada roadmap ao schema mais especifico disponivel.
3. O supervisor deve distinguir claramente `read_write`, `read_only` e `blocked`.
4. O supervisor deve impedir selecao automatica de snapshots.
5. O supervisor deve explicar por que um candidato nao pode ser usado para operacao mutavel.
6. O algoritmo deve ser deterministico para o mesmo conjunto de arquivos.

## Criterios de Aceitacao

- O documento define estrategia de roadmap ativo sem assumir `roadmap.json` unico.
- O documento cobre candidatos `roadmap*.json` e `roadmap*.schema.json`.
- A resolucao diferencia candidatos de raiz e de snapshot.
- O backend consegue devolver plugin ativo, lista de candidatos e razoes de bloqueio.
- Um candidato com parse ou schema invalido nunca e promovido a operacao mutavel.
