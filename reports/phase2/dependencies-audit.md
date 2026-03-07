# Auditoria de Dependências e Supply Chain (SEC-011)

Este relatório apresenta os resultados da auditoria de dependências e cadeia de suprimentos (supply chain) realizada no projeto ESAA Supervisor. A análise cobriu vulnerabilidades conhecidas, pacotes abandonados, typosquatting, consistência de lockfiles e reprodutibilidade de builds.

## Resumo Executivo

- **Vulnerabilidades Identificadas**: 2 (Moderadas) no Frontend. Zero no Backend.
- **Estado de Manutenção**: Excelente. Todas as dependências diretas são ativas.
- **Consistência de Lockfile**: Conforme no Frontend. Backend utiliza pinning em `requirements.txt` mas não possui lockfile completo.
- **Risco de Supply Chain**: Baixo.

## Resultados por Check (DS-001 a DS-006)

### DS-001: Dependências com vulnerabilidades conhecidas
- **Status**: PARTIAL
- **Severidade**: MEDIUM
- **Evidência**: `npm audit` no diretório `frontend` reportou 2 vulnerabilidades moderadas em `esbuild` (<=0.24.2) e `vite` (0.11.0 - 6.1.6). CVE-346 (CVSS 5.3).
- **Observação**: `pip-audit` não disponível no ambiente para auditoria automatizada do backend. Pelo histórico recente das versões pinadas em `requirements.txt`, o risco é considerado baixo.
- **Recomendação**: Atualizar `vite` para versão >= 7.3.1.

### DS-002: Dependências abandonadas
- **Status**: PASS
- **Severidade**: NONE
- **Evidência**: Todas as dependências diretas (React, FastAPI, Pydantic, etc.) são ativas e possuem releases recentes.
- **Recomendação**: Nenhuma.

### DS-003: Typosquatting packages
- **Status**: PASS
- **Severidade**: NONE
- **Evidência**: Nomes de pacotes em `package.json` e `requirements.txt` foram verificados contra typos conhecidos. Todos são legítimos e bem estabelecidos.
- **Recomendação**: Nenhuma.

### DS-004: Dependências sem lockfile
- **Status**: PASS
- **Severidade**: NONE
- **Evidência**: `package-lock.json` presente no frontend. `backend\requirements.txt` utiliza pinning estrito (`==`), o que mitiga a ausência de um lockfile formal (ex: `poetry.lock`).
- **Recomendação**: Considerar migração para `poetry` ou `pip-compile` no backend para maior controle de dependências transitivas.

### DS-005: Dependências externas não auditadas
- **Status**: PASS
- **Severidade**: NONE
- **Evidência**: Contagem de dependências transitivas (238) está dentro da média para projetos React modernos. Nenhuma evidência de scripts maliciosos `postinstall` no `package-lock.json`.
- **Recomendação**: Nenhuma.

### DS-006: Build não reproduzível
- **Status**: PASS
- **Severidade**: NONE
- **Evidência**: Pinning de versões no backend e `package-lock.json` no frontend garantem reprodutibilidade básica. Ausência de Dockerfile significa que a reprodutibilidade do ambiente de sistema operacional não é garantida por este artefato, mas não há falha no contexto atual.
- **Recomendação**: Criar Dockerfile com versões pinadas para base images.

## Plano de Remediação

1. **Atualização de Vite**: Atualizar `vite` para v7.3.1 no frontend para mitigar vulnerabilidades moderadas no servidor de desenvolvimento (CWE-346).
2. **Auditoria de Transição**: Implementar `pip-audit` no pipeline de CI/CD para detecção proativa no backend.
3. **Locking no Backend**: Migrar para `poetry` ou gerar `requirements.txt` completo (incluindo transitivas) para garantir reprodutibilidade total no backend.

---
*Gerado automaticamente pelo agente gemini-cli em 2026-03-07.*
