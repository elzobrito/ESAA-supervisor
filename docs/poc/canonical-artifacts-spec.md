# ESAA Supervisor PoC - Especificacao de Artefatos Canonicos

## Objetivo

Definir como o supervisor descobre, classifica, valida e apresenta os artefatos da pasta `.roadmap/`, tratando essa pasta como pacote canonico do projeto. A especificacao cobre o catalogo de artefatos, as regras de discovery, os checks minimos de parse e integridade e a forma como cada artefato deve ser exposto para backend e frontend.

## Escopo

Esta especificacao se aplica a:

- discovery local da pasta `.roadmap/`
- classificacao de artefatos canonicos e auxiliares
- indexacao de snapshots
- descoberta de perfis `PARCER_PROFILE*.yaml`
- descoberta de candidatos `roadmap*.json` e `roadmap*.schema.json`
- relatorio de parse, schema, integridade e papel operacional de cada artefato

Fica fora de escopo:

- implementacao da UI
- estrategia de lock de execucao
- algoritmos de selecao de task elegivel
- execucao de agentes

## Escopo de Pastas

O supervisor deve tratar a raiz `.roadmap/` como escopo primario e `snapshots/` como escopo secundario de referencia e recuperacao. Arquivos fora desses limites nao fazem parte do pacote canonico da PoC.

- `root`: arquivos diretamente em `.roadmap/`; podem participar da operacao normal
- `snapshot`: arquivos sob `.roadmap/snapshots/**`; sao indexados, mas nao entram na operacao mutavel por padrao

## Modelo Canonico de Artefato

Cada artefato descoberto deve gerar um registro de catalogo com os campos abaixo:

- `artifact_id`: identificador deterministico derivado do caminho relativo
- `path`: caminho relativo a raiz do projeto
- `scope`: `root` ou `snapshot`
- `category`: `event_store`, `projection`, `schema`, `contract`, `policy`, `profile`, `registry`, `bootstrap`, `template`, `snapshot_meta` ou `auxiliary`
- `role`: papel operacional do artefato
- `format`: `json`, `jsonl`, `yaml`, `md` ou `unknown`
- `singleton_key`: nome canonico quando o arquivo for singleton conhecido
- `plugin_id`: preenchido apenas para candidatos `roadmap*`
- `parse_status`: `ok`, `warning`, `error` ou `not_applicable`
- `schema_status`: `ok`, `missing`, `error` ou `not_applicable`
- `integrity_status`: `ok`, `warning`, `error` ou `blocked`
- `operational_state`: `active_candidate`, `read_only`, `blocked`, `supporting` ou `ignored`
- `details`: lista de mensagens objetivas para UI e logs

## Taxonomia Canonica

### 1. Source of truth

- `.roadmap/activity.jsonl`
  - categoria: `event_store`
  - papel: log append-only e fonte de verdade temporal
  - obrigatorio para operacao mutavel

### 2. Read models e projecoes

- `.roadmap/roadmap.json`
- `.roadmap/issues.json`
- `.roadmap/lessons.json`
- qualquer `.roadmap/roadmap*.json`

Papel:

- materializar estado derivado para operacao, auditoria e UI
- permitir multiplas projecoes de roadmap, sem assumir unicidade de `roadmap.json`

### 3. Schemas

- `.roadmap/roadmap.schema.json`
- `.roadmap/issues.schema.json`
- `.roadmap/lessons.schema.json`
- `.roadmap/agent_result.schema.json`
- qualquer `.roadmap/roadmap*.schema.json`

Papel:

- validar estrutura e bloquear uso operacional de artefatos invalidos

### 4. Contratos e politicas

- `.roadmap/AGENT_CONTRACT.yaml`
- `.roadmap/ORCHESTRATOR_CONTRACT.yaml`
- `.roadmap/RUNTIME_POLICY.yaml`
- `.roadmap/STORAGE_POLICY.yaml`
- `.roadmap/PROJECTION_SPEC.md`

Papel:

- governanca do runtime, validacao de outputs e projecao de estado

### 5. Perfis e registro de agentes

- `.roadmap/agents_swarm.yaml`
- `.roadmap/PARCER_PROFILE*.yaml`

Papel:

- resolver agente por `task_kind`
- descrever perfis PARCER disponiveis para spec, impl, qa e runtime

### 6. Bootstrap e templates

- `.roadmap/init.yaml`
- `.roadmap/activity_future_templates.jsonl`

Papel:

- bootstrap de execucao
- exemplos e templates de eventos futuros

### 7. Snapshots

- `.roadmap/snapshots/**`

Papel:

- referencia historica e recuperacao
- nunca sao mutados pela operacao normal

## Discovery

O discovery deve ser deterministico e executar nesta ordem:

1. Enumerar arquivos da raiz `.roadmap/`.
2. Classificar singletons conhecidos por nome exato.
3. Coletar `PARCER_PROFILE*.yaml` na raiz.
4. Coletar candidatos `roadmap*.json` e `roadmap*.schema.json` na raiz.
5. Indexar `snapshots/**` recursivamente, preservando o nome do snapshot.
6. Classificar arquivos desconhecidos como `auxiliary`, sem falhar o discovery.

Regras:

- discovery nao pode depender da existencia de um unico `roadmap.json`
- discovery nao pode promover arquivos em `snapshots/` a candidatos ativos por padrao
- arquivos desconhecidos nao sao erro estrutural por si so
- paths devem ser normalizados para formato com `/`

## Regras de Classificacao

### Singletons conhecidos

Os nomes abaixo devem ser tratados como singletons conhecidos de raiz:

- `activity.jsonl`
- `issues.json`
- `lessons.json`
- `AGENT_CONTRACT.yaml`
- `ORCHESTRATOR_CONTRACT.yaml`
- `RUNTIME_POLICY.yaml`
- `STORAGE_POLICY.yaml`
- `PROJECTION_SPEC.md`
- `agent_result.schema.json`
- `roadmap.schema.json`
- `issues.schema.json`
- `lessons.schema.json`
- `agents_swarm.yaml`
- `init.yaml`
- `activity_future_templates.jsonl`

### Perfis PARCER

Todo arquivo que casar com `PARCER_PROFILE*.yaml` deve ser catalogado como `profile`. O catalogo deve extrair, quando possivel:

- `parcer_profile.id`
- `parcer_profile.version`
- `applies_to_task_kind`, quando existir
- actor ou role principal

### Roadmap plugins e projecoes

Todo arquivo que casar com `roadmap*.json` deve ser catalogado como `projection`. Todo arquivo que casar com `roadmap*.schema.json` deve ser catalogado como `schema` associado a plugin.

O caso `roadmap.json` e `roadmap.schema.json` e apenas o plugin default, nao uma excecao hardcoded.

## Parse, Validacao e Integridade

### Parse por formato

- `json`: parse via JSON estrito
- `jsonl`: parse linha a linha, ignorando linhas vazias
- `yaml`: parse YAML seguro
- `md`: apenas leitura e existencia; sem schema

### Validacao estrutural minima

`activity.jsonl`:

- cada evento deve conter `schema_version`, `event_id`, `event_seq`, `ts`, `actor`, `action` e `payload`
- `event_seq` deve ser monotono, sem gaps
- `action` deve pertencer ao vocabulario canonico

`roadmap*.json`:

- validar contra schema associado
- confirmar existencia de `meta`, `project`, `tasks` e `indexes`
- confirmar que `status in_progress`, `review` e `done` carregam `assigned_to` e `started_at`

`issues.json` e `lessons.json`:

- validar contra schema proprio quando disponivel
- confirmar que `source_event_store` aponta para `.roadmap/activity.jsonl`

Contratos e politicas:

- parse YAML obrigatorio
- `contract_version` ou `version` deve ser legivel para exibicao

Perfis PARCER:

- parse YAML obrigatorio
- `parcer_profile.id` e `parcer_profile.version` devem ser extraidos quando presentes

### Integridade cruzada

O registry deve executar checks de relacao entre artefatos:

- `issues.json.meta.source_event_store` e `lessons.json.meta.source_event_store` devem apontar para o event store canonico
- `roadmap.meta.run.verify_status` deve ser propagado para o estado operacional do plugin
- ausencia de schema aplicavel reduz o artefato a `read_only`
- divergencia entre formato esperado e conteudo real gera `integrity_status=error`

O supervisor deve expor divergencia, nao mascara-la. Exemplo: se o roadmap projetado nao for reprodutivel pelo event store, o registry deve marcar o plugin como degradado ou bloqueado em vez de operar silenciosamente.

## Contrato do Catalogo para Backend/UI

O discovery deve retornar um pacote com:

- `artifacts`: lista de descritores de artefato
- `indexes.by_category`
- `indexes.by_scope`
- `indexes.by_plugin_id`
- `summary`

`summary` deve incluir:

- quantidade total por categoria
- quantidade de erros de parse
- quantidade de erros de schema
- quantidade de artefatos bloqueados
- plugin default detectado
- snapshots detectados

## Requisitos

1. O supervisor deve descobrir e classificar `activity`, `issues`, `lessons`, contratos, politicas, schemas, perfis PARCER, `agents_swarm` e candidatos `roadmap*`.
2. O supervisor deve tratar `roadmap.json` como plugin default, nao como unica projecao possivel.
3. O supervisor deve indexar `snapshots/**` separadamente da raiz operacional.
4. O supervisor deve reportar por artefato os estados de parse, schema, integridade e papel operacional.
5. O supervisor deve manter arquivos desconhecidos visiveis como `auxiliary`, sem abortar o discovery.
6. O supervisor deve produzir saida deterministica para o mesmo filesystem.
7. O supervisor deve bloquear uso mutavel de artefatos com erro estrutural ou sem schema aplicavel.

## Criterios de Aceitacao

- O catalogo cobre discovery de `activity`, `issues`, `lessons`, contratos, politicas, schemas, perfis PARCER, `agents_swarm` e `roadmap plugins`.
- A especificacao nao assume `roadmap.json` unico; ela permite multiplos `roadmap*.json`.
- `snapshots/` e indexado, mas nao confundido com escopo operacional mutavel.
- Cada artefato descoberto recebe categoria, papel, estado de parse, estado de schema e estado de integridade.
- O backend consegue usar o catalogo para alimentar tanto selecao de plugin quanto painel de artefatos canonicos.
