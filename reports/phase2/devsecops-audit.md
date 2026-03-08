# Auditoria de DevSecOps - SEC-022

A auditoria do domínio de **DevSecOps** no sistema **ESAA-supervisor (PoC)** avaliou seis controles fundamentais (`DO-001` a `DO-006`) relacionados à segurança no ciclo de vida de desenvolvimento e operação. Como o sistema é uma Prova de Conceito (PoC) focada em execução local supervisionada, a infraestrutura de CI/CD e as ferramentas automatizadas de segurança ainda não foram implementadas, resultando em uma postura reativa de segurança.

## Sumário de Resultados

| ID | Controle | Status | Severidade | Observação |
|:---|:---|:---:|:---:|:---|
| DO-001 | Ausência de code review | **FAIL** | MEDIUM | Não foram encontrados arquivos de `CODEOWNERS` ou configurações de branch protection no repositório. |
| DO-002 | Pipeline sem análise de segurança | **FAIL** | MEDIUM | Ausência de arquivos de configuração de CI/CD (`.github/workflows`, `.gitlab-ci.yml`, `Jenkinsfile`). |
| DO-003 | Secrets scanning ausente | **FAIL** | HIGH | Não há ferramentas de scan de segredos (gitleaks, trufflehog) ou hooks de pre-commit configurados. |
| DO-004 | SAST não implementado | **FAIL** | MEDIUM | Nenhuma ferramenta de Static Application Security Testing (Semgrep, SonarQube, Bandit) integrada ao fluxo. |
| DO-005 | DAST não implementado | **FAIL** | LOW | Ausência de Dynamic Application Security Testing (ZAP, Nuclei) para validação em runtime. |
| DO-006 | Deploy sem auditoria | **FAIL** | MEDIUM | Não há scripts de deploy ou trilha de auditoria específica para o processo de publicação do sistema. |

---

## Detalhamento dos Achados

### 1. Governança e Code Review (DO-001)
Não existem evidências de governança automatizada sobre o código-fonte. O repositório não utiliza `CODEOWNERS` para designar responsáveis por áreas críticas (como `backend/app/core` ou `src/esaa/store.py`). Embora o fluxo ESAA utilize `review -> approve` para tarefas do roadmap, isso se aplica ao estado operacional e não ao controle de versão do código (Git).

### 2. Automação de Segurança (DO-002, DO-004, DO-005)
A ausência de uma esteira de CI/CD (Continuous Integration / Continuous Deployment) impede a execução de análises proativas. 
- **SAST**: O projeto não utiliza linters de segurança (como `bandit` para Python ou `eslint-plugin-security` para JS).
- **DAST**: Não há testes dinâmicos automatizados contra a API FastAPI ou o frontend React.
- **Pipeline**: O único script de automação encontrado (`scripts/run_poc_smoke.sh`) foca em testes de fumaça funcionais, sem verificações de segurança.

### 3. Gestão de Segredos e Pre-commit (DO-003)
O risco de commit acidental de credenciais é alto. A auditoria anterior (`SEC-010`) já identificou riscos de exfiltração de dados via logs, e a falta de um scanner de segredos (`gitleaks`) ou de um framework de `pre-commit` aumenta a probabilidade de segredos chegarem ao histórico do Git.

### 4. Auditoria de Deploy (DO-006)
O processo de deploy para ambientes além do localhost não está formalizado. Sem scripts de deploy automatizados, não há registro auditável de *quem*, *quando* e *o quê* foi publicado, dificultando a rastreabilidade e a reversão (rollback) em caso de incidentes.

---

## Recomendações

1. **Implementar CI/CD**: Criar pipelines (ex: GitHub Actions) que executem testes e linting em todo Pull Request.
2. **Adicionar SAST e Secrets Scanning**: Integrar `semgrep` e `gitleaks` na pipeline para bloquear o merge de vulnerabilidades conhecidas ou segredos.
3. **Configurar CODEOWNERS**: Definir responsáveis obrigatórios para revisões de código em arquivos do núcleo do ESAA e do backend.
4. **Adotar Pre-commit Hooks**: Instalar o framework `pre-commit` para validar segurança localmente antes do push.
5. **Auditoria de Deploy**: Desenvolver scripts de deploy que registrem metadados (commit hash, user, timestamp) em um log de auditoria persistente.

---
**Auditoria realizada por:** gemini-cli
**Data:** 2026-03-08
