# SEC-041 - Boas praticas de seguranca por dominio

## Objetivo

Consolidar um baseline de seguranca acionavel para o ESAA Supervisor, organizado por dominio e alinhado com referencias oficiais da OWASP, CIS e NIST. Este documento parte dos artefatos reais da auditoria (`reports/phase1`, `reports/phase2/results`, `reports/phase3`) e nao do roadmap isoladamente.

## Contexto do sistema auditado

- Monorepo local com backend FastAPI em Python, frontend React/Vite em TypeScript e armazenamento canonico baseado em arquivos JSON/JSONL na pasta `.roadmap`.
- O backend executa CLIs de agentes por subprocesso e expoe APIs operacionais, leitura de artefatos e streaming SSE de logs.
- Nao ha autenticacao, autorizacao, reverse proxy, CI/CD formal, WAF, controle de retencao, ou protecao consistente de segredos no estado atual.
- Os achados mais graves concentram-se em controle de acesso, configuracao insegura, logs sem sanitizacao, validacao de entrada, ausencia de hardening de API e seguranca de IA/LLM.

## Como ler este documento

- `Aplicabilidade imediata`: deve entrar no baseline atual, mesmo para a PoC local.
- `Aplicabilidade antes de multiusuario`: deve ser implementada antes de uso compartilhado por equipes ou operadores reais.
- `Aplicabilidade antes de exposicao externa`: obrigatoria antes de publicar o sistema fora de uma rede local controlada.
- `Aplicabilidade condicional`: obrigatoria assim que a funcionalidade correspondente existir no produto.

## Priorizacao por aplicabilidade

| Faixa | Controles que entram primeiro |
| --- | --- |
| Agora | autorizacao de rotas, sandbox de filesystem, sanitizacao de logs, validacao de entrada, limite de privilegio dos agentes, backups do event store, higiene de dependencias |
| Antes de multiusuario | autenticacao, sessao com TTL, rate limiting, idempotencia, headers de seguranca, politica de retencao, matriz de papeis |
| Antes de exposicao externa | TLS, WAF, segmentacao, DDoS protection, CI/CD com gates de seguranca, varredura continua de segredos, DAST |
| Condicional | MFA, reset de senha, portabilidade/exclusao de dados, fluxo formal de incidentes, controles de upload com malware scan |

## 1. Governanca, arquitetura e trilha canonica

Aplicabilidade no ESAA: imediata.

Boas praticas:

- Tratar `.roadmap/activity.jsonl` como trilha canonica e impedir mutacoes paralelas em projecoes sem reproject + verify.
- Manter `claim -> complete -> review` como gate obrigatorio em qualquer automacao de agentes.
- Exigir dono explicito para cada superficie critica: `.roadmap`, backend API, frontend, adapters de agentes e artefatos de auditoria.
- Catalogar ativos e fronteiras de confianca: browser, FastAPI, `.roadmap`, subprocessos de agentes e logs SSE.
- Formalizar criterios de rollout: o que e aceitavel em PoC local nao e aceitavel em ambiente multiusuario ou exposto.

Referencias-base:

- OWASP ASVS 5.0.0
- CIS Controls v8.1: 1 (Enterprise Assets), 4 (Secure Configuration), 8 (Audit Log Management), 17 (Incident Response Management)
- NIST CSF 2.0: Govern, Identify, Protect
- NIST SP 800-53 Rev. 5 / Release 5.2.0: AC, AU, CM, PL, SA

Achados relacionados:

- SC-004, SC-008, AZ-001, AI-002, IF-005, DO-006

## 2. Secrets, configuracao e hardening basico

Aplicabilidade no ESAA: imediata.

Boas praticas:

- Restringir CORS por ambiente e por origem confiavel; nunca usar wildcard em conjunto com credenciais.
- Remover `.env` reais do repositorio; manter apenas `.env.example` com placeholders.
- Separar claramente configuracao de dev, staging e producao; desabilitar modos verbosos fora de dev.
- Redigir ou mascarar tokens, cookies, prompts e comandos antes de persistir ou transmitir logs.
- Revisar configuracoes padrao de portas, hosts, flags e comandos de agentes para garantir least privilege.

Referencias-base:

- OWASP Top 10:2021 A05 Security Misconfiguration, A02 Cryptographic Failures, A09 Security Logging and Monitoring Failures
- OWASP ASVS 5.0.0
- CIS Controls v8.1: 3 (Data Protection), 4 (Secure Configuration), 8 (Audit Log Management)
- NIST CSF 2.0: Protect, Detect
- NIST SP 800-53 Rev. 5 / Release 5.2.0: CM, SC, AU, SI

Achados relacionados:

- SC-003, SC-004, SC-005, SC-007, SC-008

## 3. Autenticacao e gerenciamento de sessao

Aplicabilidade no ESAA: antes de multiusuario. MFA e fluxo de recuperacao sao condicionais ao primeiro rollout de identidade real.

Boas praticas:

- Introduzir autenticacao forte antes de permitir uso por operadores reais; nao depender de "seguranca por ambiente local".
- Armazenar credenciais apenas com hash resistente a offline cracking.
- Definir TTL de sessao, reautenticacao para acoes sensiveis e invalidacao no logout.
- Planejar MFA para administradores e revisores assim que houver contas humanas persistentes.
- Implementar reset e recuperacao com token de uso unico, expiracao curta e trilha de auditoria.
- Adotar identificadores de sessao imprevisiveis, rotacao apos autenticacao e cookies `HttpOnly`, `Secure` e `SameSite`.

Referencias-base:

- OWASP Top 10:2021 A07 Identification and Authentication Failures
- OWASP ASVS 5.0.0
- CIS Controls v8.1: 5 (Account Management), 6 (Access Control Management)
- NIST CSF 2.0: Protect
- NIST SP 800-63B-4 (Authentication and Authenticator Management)
- NIST SP 800-53 Rev. 5 / Release 5.2.0: IA, AC

Achados relacionados:

- AU-001, AU-002, AU-003, AU-004, AU-005, AU-006, AU-007, AU-008
- SS-001, SS-002, SS-003, SS-005, SS-006

## 4. Autorizacao, papeis e operacoes administrativas

Aplicabilidade no ESAA: imediata.

Boas praticas:

- Proteger todas as rotas mutativas e de leitura sensivel no backend; o frontend nunca pode ser o unico ponto de enforcement.
- Definir RBAC minimo para `admin`, `operator`, `reviewer` e `auditor`, com privilegio minimo por acao.
- Bloquear acesso arbitrario ao filesystem; `browse/open` deve operar apenas dentro de um root aprovado.
- Exigir dupla verificacao para reset, review, replay de runs e reparos de integridade.
- Modelar ownership de projeto e de run para evitar que um operador veja ou altere o escopo de outro.

Referencias-base:

- OWASP Top 10:2021 A01 Broken Access Control
- OWASP ASVS 5.0.0
- CIS Controls v8.1: 5 (Account Management), 6 (Access Control Management)
- NIST CSF 2.0: Govern, Protect
- NIST SP 800-53 Rev. 5 / Release 5.2.0: AC, IA, AU

Achados relacionados:

- AZ-001, AZ-002, AZ-003, AZ-004, AZ-005, AZ-006

## 5. Seguranca de API e contratos HTTP

Aplicabilidade no ESAA: imediata para rate limit, paginacao e escopo de resposta; antes de exposicao externa para controles mais agressivos de borda.

Boas praticas:

- Aplicar rate limiting por endpoint, IP e identidade de sessao em rotas de alto custo.
- Introduzir idempotency keys em operacoes mutativas como `run.start`, `task.reset`, `issue.resolve` e mensagens de chat.
- Paginar listas extensas e reduzir over-fetching em `/state`, `/browse` e historicos.
- Reduzir payloads ao minimo necessario; nao devolver campos internos, comandos completos ou blobs de log sem necessidade operacional.
- Versionar contratos de API e registrar mudancas que afetem automacoes.

Referencias-base:

- OWASP Top 10:2021 A04 Insecure Design, A05 Security Misconfiguration, A10 Server-Side Request Forgery
- OWASP ASVS 5.0.0
- CIS Controls v8.1: 4 (Secure Configuration), 12 (Network Infrastructure Management), 13 (Network Monitoring and Defense), 16 (Application Software Security)
- NIST CSF 2.0: Protect, Detect
- NIST SP 800-53 Rev. 5 / Release 5.2.0: AC, SC, SI

Achados relacionados:

- AP-001, AP-002, AP-003, AP-006, AP-007

## 6. Validacao de entrada, upload e isolamento de arquivos

Aplicabilidade no ESAA: imediata.

Boas praticas:

- Validar todos os identificadores recebidos por API antes de formar caminhos, nomes de arquivo ou comandos.
- Normalizar e resolver paths antes do acesso ao disco; negar traversal e paths fora do diretorio permitido.
- Aplicar limites de tamanho, tipo MIME, extensao, nome de arquivo e cota por upload.
- Armazenar uploads em area isolada, sem permissao de execucao, com nome interno gerado pelo sistema.
- Se uploads forem habilitados em ambiente real, incluir scanning antimalware e rejeicao de conteudo executavel.

Referencias-base:

- OWASP Top 10:2021 A03 Injection, A04 Insecure Design
- OWASP ASVS 5.0.0
- CIS Controls v8.1: 4 (Secure Configuration), 9 (Email and Web Browser Protections), 16 (Application Software Security)
- NIST CSF 2.0: Protect
- NIST SP 800-53 Rev. 5 / Release 5.2.0: SI, SC, AC

Achados relacionados:

- IV-003, IV-006, IV-007
- FU-001, FU-002, FU-004, FU-005

## 7. Criptografia, transporte e headers de seguranca

Aplicabilidade no ESAA: antes de exposicao externa. Alguns controles, como design para criptografia at-rest e CSP, devem entrar agora no backlog.

Boas praticas:

- Encerrar TLS em reverse proxy ou gateway confiavel; evitar qualquer operacao via HTTP puro fora de loopback local.
- Proteger segredos e dados sensiveis em repouso quando houver persistencia de dados de operador, prompts, outputs ou artefatos confidenciais.
- Aplicar CSP, HSTS, `X-Content-Type-Options`, `X-Frame-Options` e `Referrer-Policy` em frontend e API publicados.
- Definir estrategia de rotacao de chaves e segregacao entre chaves de dev e de producao.
- Classificar quais dados realmente exigem criptografia at-rest e quais precisam apenas de controle de acesso forte e backup seguro.

Referencias-base:

- OWASP Top 10:2021 A02 Cryptographic Failures, A05 Security Misconfiguration
- OWASP ASVS 5.0.0
- CIS Controls v8.1: 3 (Data Protection), 4 (Secure Configuration), 12 (Network Infrastructure Management), 13 (Network Monitoring and Defense)
- NIST CSF 2.0: Protect
- NIST SP 800-53 Rev. 5 / Release 5.2.0: SC, CM, IA

Achados relacionados:

- CR-001, CR-003, CR-004, CR-005
- SH-001, SH-002, SH-003, SH-004, SH-005
- IF-001

## 8. Logging, monitoramento e evidencias de auditoria

Aplicabilidade no ESAA: imediata.

Boas praticas:

- Tratar logs de agentes como dados sensiveis; aplicar mascaramento antes de qualquer persistencia ou SSE.
- Anexar correlation IDs do request ate subprocessos, eventos e revisoes para rastreabilidade ponta a ponta.
- Registrar eventos de seguranca e operacao com semantica consistente, nao apenas stdout/stderr cru.
- Separar logs tecnicos, logs de seguranca e trilha canonica do workflow para reduzir ruido e facilitar deteccao.
- Definir alertas para falhas de verify, tentativa de traversal, saida invalida de agente, repeticao anomala de runs e mutacoes bloqueadas.

Referencias-base:

- OWASP Top 10:2021 A09 Security Logging and Monitoring Failures
- OWASP ASVS 5.0.0
- CIS Controls v8.1: 8 (Audit Log Management), 13 (Network Monitoring and Defense), 17 (Incident Response Management)
- NIST CSF 2.0: Detect, Respond
- NIST SP 800-53 Rev. 5 / Release 5.2.0: AU, IR, SI

Achados relacionados:

- LM-001, LM-004, LM-005
- SC-008, AI-005

## 9. Protecao de dados, retencao e privacidade

Aplicabilidade no ESAA: imediata para minimizacao e retencao; antes de multiusuario para programa minimo de privacidade; obrigatoria antes de uso com dados reais.

Boas praticas:

- Minimizar o que vai para `chat_sessions`, `activity.jsonl`, metadata de mensagens e artefatos exportados.
- Definir politica de retencao por categoria: eventos canonicos, sessoes de chat, logs tecnicos, relatorios e arquivos temporarios.
- Separar dados necessarios para auditabilidade daqueles que sao apenas conveniencia de depuracao.
- Implementar anonimizacao ou pseudonimizacao onde o conteudo puder conter dados de usuarios, prompts ou segredos.
- Planejar consentimento, base legal, direito de exclusao/exportacao e inventario de tratamento antes de qualquer uso com dados pessoais reais.

Referencias-base:

- OWASP Top 10:2021 A02 Cryptographic Failures, A09 Security Logging and Monitoring Failures
- OWASP ASVS 5.0.0
- CIS Controls v8.1: 3 (Data Protection), 8 (Audit Log Management), 11 (Data Recovery)
- NIST CSF 2.0: Govern, Protect, Recover
- NIST SP 800-53 Rev. 5 / Release 5.2.0: AU, CP, MP, SC

Achados relacionados:

- DA-001, DA-002, DA-003, DA-004, DA-005

## 10. Dependencias, frontend e DevSecOps

Aplicabilidade no ESAA: imediata.

Boas praticas:

- Atualizar dependencias vulneraveis e bloquear merge quando houver CVEs graves sem mitigacao aprovada.
- Implantar secrets scanning, SAST e verificacoes de lockfile em PRs.
- Adotar branch protection, revisao obrigatoria e donos tecnicos para areas criticas.
- Evitar tokens de autenticacao em `localStorage`; se autenticacao for adicionada, preferir cookies `HttpOnly`.
- Garantir que o frontend nao seja fonte de verdade para permissoes, validacoes criticas ou fluxos administrativos.
- Incluir DAST em staging antes de qualquer exposicao publica.

Referencias-base:

- OWASP Top 10:2021 A06 Vulnerable and Outdated Components, A08 Software and Data Integrity Failures, A05 Security Misconfiguration
- OWASP ASVS 5.0.0
- CIS Controls v8.1: 2 (Software Assets), 7 (Continuous Vulnerability Management), 16 (Application Software Security), 18 (Penetration Testing)
- NIST CSF 2.0: Govern, Protect, Detect
- NIST SP 800-53 Rev. 5 / Release 5.2.0: RA, SA, SI, CM

Achados relacionados:

- DS-001
- DO-001, DO-002, DO-003, DO-004, DO-005, DO-006
- FE-003

## 11. Infraestrutura, disponibilidade e recuperacao

Aplicabilidade no ESAA: backups e recuperacao sao imediatos; WAF, DDoS, segmentacao e firewall tornam-se obrigatorios antes de exposicao externa.

Boas praticas:

- Fazer backup testado de `activity.jsonl`, `roadmap*.json`, `issues.json`, `lessons.json` e `chat_sessions`.
- Definir RPO/RTO e procedimento de restauracao para o event store, ja que ele e a fonte de verdade operacional.
- Publicar a API atras de reverse proxy com TLS, firewall e limites de conexao.
- Segmentar frontend, backend e armazenamento quando sair do modo local.
- Considerar WAF e protecao DDoS ao publicar endpoints ou SSE para redes amplas.

Referencias-base:

- OWASP Top 10:2021 A05 Security Misconfiguration
- OWASP ASVS 5.0.0
- CIS Controls v8.1: 11 (Data Recovery), 12 (Network Infrastructure Management), 13 (Network Monitoring and Defense)
- NIST CSF 2.0: Protect, Detect, Recover
- NIST SP 800-53 Rev. 5 / Release 5.2.0: CP, SC, SI

Achados relacionados:

- IF-001, IF-002, IF-003, IF-004, IF-005, IF-006

## 12. IA/LLM e execucao de agentes

Aplicabilidade no ESAA: imediata.

Boas praticas:

- Separar rigidamente system prompt, contexto operacional e entrada do usuario com delimitadores estruturados.
- Desativar modos de execucao que removam approvals ou ampliem indevidamente o escopo das ferramentas.
- Validar tamanho, formato e risco do input antes de enviar ao modelo.
- Restringir tools por tarefa e por runner; qualquer acao destrutiva deve continuar dependente de aprovacao humana.
- Sanitizar output do LLM antes de renderizar ou persistir; remover links externos, HTML perigoso e vazamento de prompt interno.
- Registrar decisao de tool use, contexto de risco e resultado de execucao em trilha auditavel.

Referencias-base:

- OWASP Top 10:2021 A03 Injection, A04 Insecure Design, A08 Software and Data Integrity Failures, A09 Security Logging and Monitoring Failures
- OWASP ASVS 5.0.0
- CIS Controls v8.1: 4 (Secure Configuration), 6 (Access Control Management), 8 (Audit Log Management), 16 (Application Software Security)
- NIST CSF 2.0: Govern, Protect, Detect
- NIST SP 800-53 Rev. 5 / Release 5.2.0: AC, AU, SA, SI

Achados relacionados:

- AI-001, AI-002, AI-003, AI-004, AI-005

## Baseline minimo recomendado para a proxima fase

1. Fechar autorizacao e sandbox de filesystem antes de qualquer outro hardening incremental.
2. Sanitizar logs, limitar privilegios dos agentes e proteger a trilha canonica contra vazamento e corrupcao.
3. Colocar rate limiting, validacao de entrada e idempotencia nas rotas mutativas.
4. Estabelecer backup e restauracao de `activity.jsonl` e das projecoes compartilhadas.
5. Planejar autenticacao, sessao e papeis antes de qualquer uso multiusuario.
6. Levar TLS, headers, WAF, segmentacao e DAST para o gate de exposicao externa.

## Referencias oficiais consultadas

As referencias abaixo estavam atuais na data de consulta desta task (2026-03-08):

- OWASP Application Security Verification Standard (ASVS) 5.0.0: https://owasp.org/www-project-application-security-verification-standard/
- OWASP Top 10:2021: https://owasp.org/Top10/2021/
- CIS Critical Security Controls v8.1: https://www.cisecurity.org/controls/v8-1
- NIST Cybersecurity Framework (CSF) 2.0: https://www.nist.gov/publications/nist-cybersecurity-framework-csf-20
- NIST SP 800-53 Rev. 5, current release 5.2.0: https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final
- NIST announcement for SP 800-53 Release 5.2.0: https://csrc.nist.gov/News/2025/nist-releases-revision-to-sp-800-53-controls
- NIST SP 800-63B-4, Authentication and Authenticator Management: https://csrc.nist.gov/pubs/sp/800/63/B/4/final
