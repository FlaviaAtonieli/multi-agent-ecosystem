# Requisitos do Portfólio

Situação do projeto frente ao [The Portfolio Playbook](https://github.com/CatolicaSC-Portfolio/The-Portfolio-Playbook), nas linhas de **Web Apps** e de **IA**. Cada item aponta para a evidência, para ser conferido no código.

Legenda: ✅ atendido e conferido | 🟡 feito, falta confirmar em produção | ⏳ pendente

## Pontos fortes

| Ponto | Evidência |
|---|---|
| **Protocolo MCP real**, tema que o guia marca como "Preferir" e pouco explorado: cada Agent Skill roda em um processo separado | [`mcp_client.py`](../backend/app/agent_catalog/mcp_client.py), testado por stdio em `test_skill_artifacts.py` |
| **RAG com qualidade medida:** Precision@3, Recall@3 e MRR contra gabarito manual | [Pipeline de IA](architecture/ai-pipeline.md) |
| **Governança de IA explicável:** Quality Gate por regras, revisão humana e `Trace ID` em cada etapa | [`quality_gate/service.py`](../backend/app/quality_gate/service.py) |
| **Comitê como escopo da orquestração:** evita chamadas de IA a skills fora do assunto | [`agent_skill_orchestration_service.py`](../backend/app/services/agent_skill_orchestration_service.py) |
| **Respostas com arquivos e ZIP**, sem gastar tokens para mostrar ou baixar | [`artifact_service.py`](../backend/app/services/artifact_service.py) |
| **Segurança além do básico:** sessão opaca, CSRF, Argon2, OAuth, código por e-mail, mascaramento de dados pessoais | [SECURITY.md](../SECURITY.md) |
| **Testes que acusam defeitos:** o código é quebrado de propósito para conferir | [Relatório de validação](validation/README.md) |
| **Engenharia:** CI, SonarCloud, imagens com hashes travados, migrações conferidas em PostgreSQL | [`ci.yml`](../.github/workflows/ci.yml) |

## Núcleo comum

| Requisito | Situação | Evidência |
|---|---|---|
| Wiki no repositório | 🟡 | [Wiki](https://github.com/FlaviaAtonieli/multi-agent-ecosystem/wiki), atualizada em 03/11/2026. Faltam os PRs #101 a #105 |
| CI/CD | 🟡 | CI, publicação das imagens e deploy do frontend automáticos. O backend ainda precisa de `az webapp restart` manual: falta o segredo `AZURE_BACKEND_DEPLOY_WEBHOOK` ([guia](deployment/azure.md)) |
| Análise estática e de segurança | ✅ | `ruff`, `mypy`, `tsc` e [SonarCloud](https://sonarcloud.io/project/overview?id=FlaviaAtonieli_multi-agent-ecosystem): quality gate OK, 0 bugs, 0 vulnerabilidades, nota A nos três critérios e 1,3% de duplicação ([05/11/2026](validation/evidence/2026-11-05-production-validation.md)) |
| Monitoramento | 🟡 | Prometheus e Grafana [prontos](deployment/monitoring.md). Em produção, o linked backend do Azure bloqueia o acesso a `/metrics`: falta liberar esse caminho |

## Linha de Web Apps

| Requisito | Situação | Evidência |
|---|---|---|
| Hospedagem pública | ✅ | Azure, aceito pelo professor. Conferido em [05/11/2026](validation/evidence/2026-11-05-production-validation.md): HTTPS, HSTS e CSP. **Precisa estar ligado até sair a nota final** |
| Funcionalidades conforme a RFC | ✅ | RF17 a RF21 acrescentados e Apêndice J da [RFC](rfc), com o motivo de cada mudança e os desvios (RF09, RNF07 e RNF08), no PR #111 |
| Interface funcional | ✅ | Jornadas conferidas no Chrome |
| Arquitetura modular | ✅ | [Visão da arquitetura](architecture/overview.md) |
| Requisitos, casos de uso e C4 | ✅ | [RFC](rfc), seções 2 e 3 |
| Instruções de deploy | ✅ | [Guia](deployment/azure.md) |
| 3 fluxos de negócio completos | ✅ | Ver abaixo. Conferidos em produção em [05/11/2026](validation/evidence/2026-11-05-production-validation.md) |
| Cobertura de 75% no backend e 25% no frontend | ✅ | Exigida pelo CI. No `main` em 05/11/2026: 85,9% no backend e 56,5% de linhas no frontend |
| TDD | 🟡 | Usado nas funcionalidades recentes, não no início do projeto. Falta saber como é cobrado |

**Fluxos de negócio:**

1. **Conta e acesso:** cadastro, login, código por e-mail, recuperação de senha e exclusão de conta.
2. **Catálogo e comitês:** criar ou importar skill, publicar, montar comitê e receber sugestões.
3. **Orquestração:** solicitação, qualificação, execução, Quality Gate, revisão humana, arquivos e perguntas.

Em produção, em 05/11/2026, foram conferidos o cadastro e o login do fluxo 1, a criação de comitê com skill do fluxo 2 e o fluxo 3 inteiro (contexto barrado, interromper, executar de novo, Quality Gate e revisão humana). Ficaram fora o código por e-mail, a recuperação de senha, a exclusão de conta, a importação de skill, as sugestões e as perguntas.

## Linha de IA

| Requisito | Situação | Evidência |
|---|---|---|
| Abordagem de IA fundamentada | ✅ | RAG é aceito pelo guia. [Pipeline de IA](architecture/ai-pipeline.md) |
| Parte de uma aplicação | ✅ | A orquestração é o fluxo principal |
| Dados justificados | ✅ | Sintéticos, com a justificativa no [pipeline](architecture/ai-pipeline.md#1-dados-e-indexação) |
| Pipeline completo | ✅ | Dados, pré-processamento, modelo e pós-processamento |
| Ética e LGPD | ✅ | Mascaramento, [política de privacidade](../frontend/src/pages/PrivacyPage.tsx) e exclusão de conta |
| Resultados replicáveis | 🟡 | Busca e métricas podem ser repetidas. O texto do modelo varia mesmo com `temperature` e `seed` fixos ([medição](validation/evidence/2026-11-05-reproducibility.md)), mas o conteúdo se repete: similaridade média de 0,79 a 0,84 entre repetições, contra no máximo 0,50 com outra pergunta ([medição](validation/evidence/2026-11-07-content-repeatability.md)). Falta a posição do professor |
| Avaliação do resultado | 🟡 | Busca medida nas 10 áreas: as 4 primeiras com o modelo pago e as 10 com modelo gratuito (medição de 06/11/2026, no PR #110). Motor de sugestão medido, com o limite escolhido por k-fold ([medição](validation/evidence/2026-11-07-suggestion-threshold-kfold.md)). Orquestração completa em produção com modelo gratuito ([05/11/2026](validation/evidence/2026-11-05-production-validation.md)). Falta avaliar a qualidade da resposta final |

## O que depende de pessoas

| Requisito | Situação |
|---|---|
| 5 orientações evidenciadas | ⏳ 4 de 5, segundo a autora |
| Review por colegas em PRs, testes cruzados e issues | 🟡 49 comentários de 2 colegas em PRs (AmandKorcz 44, PHV00 5), 9 deles com análise. Nenhuma review formal do GitHub (Approve ou Request changes) e nenhuma issue até 05/11/2026 |
| Aceite do parceiro externo e feedbacks | ⏳ Em andamento |
| Pôster A0 com QR Code | ⏳ |
| Prova de autoria | ⏳ Até 30/11/2026 |
| Visitar e avaliar colegas no Demo Day | ⏳ Em dezembro |

## Limitações conhecidas

- O limite de requisições por IP enxerga o IP da infraestrutura do Azure, não o de cada usuário.
- A execução em segundo plano assume um único processo no backend.
- A base de conhecimento só tem documentos técnicos de exemplo.
- O modelo às vezes ignora um pedido explícito de arquivos (2 de 13 tentativas com o modelo gratuito). O Quality Gate manda esses casos para revisão humana (PR #107).
- A barreira de contexto vale para o contexto. Problema e objetivo sem conteúdo passam a ser recusados no cadastro com o PR #108. O título continua livre.
- A suíte automática simula a IA. Os testes marcados com `llm` chamam o modelo real e ficam fora do CI.
