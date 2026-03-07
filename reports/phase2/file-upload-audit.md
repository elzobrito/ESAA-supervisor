# Auditoria de Segurança: Upload de Arquivos (SEC-016)

## Sumário Executivo

A auditoria do domínio de **Upload de Arquivos** no sistema ESAA-supervisor revelou que, embora não existam endpoints tradicionais de upload de arquivos via API HTTP (multipart/form-data), o sistema possui um mecanismo crítico de criação e mutação de arquivos através do fluxo de resultados de agentes (Agent Result Submission).

Este fluxo atua como um sistema de "upload funcional", onde agentes autônomos ou usuários externos submetem conteúdos que são persistidos no sistema de arquivos do servidor. A segurança deste mecanismo baseia-se quase exclusivamente no sistema de **Boundaries** (fronteiras) do ESAA, que é eficaz contra Path Traversal e violações de escopo de diretório, mas carece de proteções clássicas como limites de tamanho, validação de conteúdo (magic bytes) e varredura de malware.

## Escopo da Auditoria

- **Componentes Backend:** `app/api/routes_projects.py`, `app/core/run_engine.py`, `app/adapters/base.py`, `src/esaa/service.py`, `src/esaa/validator.py`.
- **Componentes Frontend:** `services/projects.ts`, `components/artifacts/`.
- **Playbook de Referência:** FU-001 a FU-006.

---

## Resultados por Verificação (Playbook FU)

### FU-001: Uploads sem validação de tipo
- **Status:** `FAIL`
- **Gravidade:** `HIGH`
- **Evidência:** O arquivo `src/esaa/validator.py` valida apenas o caminho (path) contra uma allowlist definida no contrato do agente. Não há inspeção de `magic bytes` ou verificação se o conteúdo condiz com a extensão declarada.
- **Remediação:** Implementar validação de assinatura de arquivo (magic bytes) antes da persistência, garantindo que o conteúdo corresponda ao tipo esperado pelo diretório de destino.

### FU-002: Uploads sem limite de tamanho
- **Status:** `FAIL`
- **Gravidade:** `MEDIUM`
- **Evidência:** Não foram encontrados limites de tamanho para o payload de `file_updates`. O método `subprocess.run` com `capture_output=True` em `app/adapters/base.py` carrega todo o output do agente na memória, e `Path.write_text` em `service.py` escreve o conteúdo sem checagem de quota ou limite.
- **Remediação:** Definir limites globais e por arquivo para atualizações submetidas por agentes. Rejeitar payloads que excedam a capacidade de processamento seguro (ex: > 10MB por arquivo).

### FU-003: Uploads armazenados no servidor da aplicação
- **Status:** `PASS (Por Design)`
- **Gravidade:** `LOW`
- **Evidência:** Como um sistema de orquestração local/PoC, o armazenamento em disco local é o comportamento pretendido. No entanto, os arquivos são servidos pela API (`read_artifact_content`), o que pode expor o servidor se houver falha na autorização (que atualmente é inexistente).
- **Remediação:** Em ambientes de produção, utilizar Object Storage (S3/GCS) para artefatos gerados ou garantir que o servidor de arquivos seja isolado e read-only para o processo da web.

### FU-004: Ausência de antivírus
- **Status:** `FAIL`
- **Gravidade:** `MEDIUM`
- **Evidência:** Não há integração com ClamAV ou qualquer serviço de varredura de malware para arquivos gerados por agentes.
- **Remediação:** Integrar um passo de varredura assíncrona ou síncrona para arquivos que entram no workspace, especialmente em ambientes multi-agente ou compartilhados.

### FU-005: Possibilidade de upload executável
- **Status:** `FAIL`
- **Gravidade:** `HIGH`
- **Evidência:** Agentes com permissão `impl` podem escrever arquivos `.py`, `.sh` ou `.js` diretamente no diretório `src/`. Embora isso seja necessário para o funcionamento do sistema, não há restrição que impeça um agente comprometido de injetar código executável em diretórios inesperados se as boundaries forem mal configuradas. Além disso, o web server não possui configurações para impedir a execução desses arquivos se fossem servidos em um contexto web direto (ex: PHP).
- **Remediação:** Endurecer as configurações do web server para não executar conteúdo de diretórios de uploads/artefatos. Implementar uma camada de "Sanitize Code" para remover patterns perigosos antes da escrita.

### FU-006: Filenames não sanitizados
- **Status:** `PASS`
- **Gravidade:** `CRITICAL`
- **Evidência:** O método `_validate_safe_path` em `src/esaa/validator.py` implementa uma defesa robusta contra Path Traversal, normalizando caminhos e bloqueando explicitamente prefixos `..` ou `/` e qualquer componente intermediário de subida de diretório.
- **Remediação:** Manter a implementação atual; considerar o uso de `pathlib` de forma mais extensiva para evitar manipulações de string brutas.

---

## Recomendações e Plano de Ação

1. **Implementar Content Validation:** Adicionar a biblioteca `file-type` ou similar ao `validator.py` para checar magic bytes.
2. **Impor Limites de Payload:** Adicionar uma configuração de `max_file_update_size` no `AGENT_CONTRACT.yaml` e validá-la no `ESAAService`.
3. **Isolamento de Execução:** Garantir que o processo que executa os agentes tenha permissões restritas no filesystem (Least Privilege), limitando-o apenas ao workspace do projeto ativo.
4. **Segurança de API:** Implementar autenticação e autorização nos endpoints de `runs` e `artifacts` para impedir que usuários não autorizados disparem execuções de agentes que resultam em escritas no disco.
