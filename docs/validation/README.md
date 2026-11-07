# Relatório de Validação

Snapshot do estado validado da PoC nesta versão. Não é um substituto das evidências
detalhadas em [`docs/validation/evidence/`](evidence) — este documento
é o ponto de partida rápido; aquelas, o registro completo por marco/critério.

## Verificações desta versão

- `ruff` e `mypy` no backend; `tsc` e build no frontend;
- autenticação por sessão opaca, CSRF (double-submit) e bloqueio após tentativas inválidas;
- login com GitHub e Google (OAuth, opcionais), código por e-mail em navegador novo e
  recuperação de senha por e-mail;
- sem papéis de usuário desde 14/10/2026: o acesso é controlado por propriedade,
  visibilidade da skill e cota de tokens (ver [`SECURITY.md`](../../SECURITY.md#autorização));
- migrations Alembic até `0021_skill_embeddings`;
- integração com a OpenRouter (Model Gateway), sem provedor mock na aplicação;
- orquestração em segundo plano, com até 3 skills em paralelo por execução, progresso
  real e recuperação de execuções interrompidas por um reinício;
- plano estruturado com aprovação humana quando o Quality Gate não aprova;
- geração de `LLM Call ID` e `Trace ID` para rastreabilidade ponta a ponta;
- hashes SHA-256 da entrada e saída, sem conteúdo integral em `llm_invocations` por padrão;
- mascaramento de e-mail, senha, token e padrões de chave antes de qualquer chamada externa;
- catálogo de Agent Skills: 10 oficiais e skills de usuário em área livre, com visibilidade
  `OFFICIAL`, `PRIVATE` (só o dono) ou `CLAN` (membros do clã);
- anexo de documentos de texto como contexto adicional de uma solicitação;
- clã obrigatório na orquestração, respostas com arquivos e ZIP, e sugestão de skills por embeddings;
- pipeline RAG com qualidade medida (Precision@k, Recall@k e MRR) em 4 das 10 áreas
  oficiais (ver [`docs/ai-pipeline.md`](../architecture/ai-pipeline.md));
- métricas de IA, execução e autenticação em `/metrics`, com painel e alertas no Grafana.

## Testes e cobertura

Conferidos em todo push e PR pelo CI, que falha abaixo das metas:

| Parte | Ferramenta | Testes (04/11/2026) | Cobertura de linhas | Meta |
|---|---|---:|---:|---:|
| Backend | pytest, em SQLite e PostgreSQL | 313 | 86% | 75% |
| Frontend | Vitest e Testing Library | 135 | 51,52% | 25% |

A contagem do backend não inclui os 27 testes marcados com `llm`, que chamam a OpenRouter de verdade e ficam fora do CI: rodar a cada push gastaria créditos reais e poderia ficar vermelho por instabilidade do provedor, não por bug de código. Em 05/11/2026 eles rodaram com modelos gratuitos: 25 de 27 passaram, e o que ficou abaixo do limite mede a qualidade da busca com um modelo de embeddings gratuito ([evidência](evidence/2026-11-05-real-llm-free-models.md)). **O modelo padrão de produção, `openai/gpt-5-mini`, não foi usado, porque é pago.**

**O que é simulado:** na suíte do CI, o modelo de linguagem e os embeddings são substituídos por versões falsas, e no frontend só a rede é simulada. Todo o restante roda de verdade. Por isso, a suíte confere as regras do sistema, não a qualidade das respostas da IA.

Para rodar, veja a seção "Testes" do [README](../../README.md#testes).

## Os testes acusam defeitos?

Cobertura mostra que uma linha rodou, não que o resultado foi conferido. Por isso, em 04/11/2026, o código foi quebrado de propósito, um ponto por vez, em cópias, e a suíte do CI rodou em cada caso.

| Rodada | Backend | Frontend |
|---|---:|---:|
| Primeira, antes dos testes novos | **19 de 34 acusadas**, 15 passaram sem ninguém perceber | 10 de 10, em 03/11/2026 |
| Depois de `tests/test_protections.py` | **35 de 35** | 12 de 12, com as telas novas |

As 15 que escaparam eram proteções reais, como o vínculo do CSRF com a sessão, o bloqueio por tentativas de login, o limite de requisições, a cota de tokens, o mascaramento de dados pessoais e o Quality Gate. Parte delas tinha teste, mas marcado com `llm`, e por isso nunca rodava no CI. A própria checagem também pegou um teste novo fraco, que recebia 403 pelo motivo errado.

**O que isso não prova:** os pontos foram escolhidos à mão entre as regras críticas, então não é uma medida da suíte inteira. A automática simula o modelo e, no frontend, a rede. Os testes marcados com `llm` são os únicos que falam com o modelo real.

## Acessibilidade

Em 04/11/2026, o [axe](https://github.com/dequelabs/axe-core), com as regras WCAG 2.1 A e AA, rodou no Chrome em todas as telas, inclusive a orquestração com resultado. A primeira rodada achou contraste insuficiente e 3 listas sem nome para leitor de tela. Depois da correção, nenhuma violação foi apontada. Ferramentas automáticas pegam só parte dos problemas de acessibilidade: não houve teste com leitor de tela nem com pessoas.

## Núcleo comum de engenharia

Itens exigidos pela rubrica independentemente da linha de projeto:

- [x] **CI/CD** — [`ci.yml`](../../.github/workflows/ci.yml) em todo push e PR, e [`publish-images.yml`](../../.github/workflows/publish-images.yml) com o [deploy do backend](../deployment/azure.md#8-deploy-automático-do-backend). O frontend é publicado pelo workflow do Static Web Apps.
- [x] **Wiki no GitHub** — [wiki do repositório](https://github.com/FlaviaAtonieli/multi-agent-ecosystem/wiki).
- [x] **Análise estática de código e segurança** — `ruff`, `mypy` e `tsc` no CI, e [SonarCloud](https://sonarcloud.io/project/overview?id=FlaviaAtonieli_multi-agent-ecosystem) em todo push e PR.
- [ ] **Monitoramento** — Prometheus, Grafana, painel e alertas estão [prontos](../deployment/monitoring.md) e foram testados contra um backend local. **Falta** ligar a leitura do backend em produção.

## Comandos locais

```powershell
docker compose up --build -d
docker compose exec backend alembic current
docker compose ps
```

Resultado esperado do `alembic current`:

```text
0021_skill_embeddings (head)
```

## Evidências detalhadas

- [Validação da fundação](evidence/2026-08-foundation-validation.md)
- [Extensibilidade plug-and-play](evidence/2026-08-plug-and-play-extensibility.md)
- [Medição de KPIs (M7)](evidence/2026-08-m7-kpi-measurement.md) — com modelo gratuito e execução em sequência; ainda não repetida com o código atual
- [Qualidade do RAG (domínio Código Legado)](evidence/2026-08-30-rag-quality-validation.md)
- [Testes com a IA real em modelos gratuitos](evidence/2026-11-05-real-llm-free-models.md) (05/11/2026)
- [Repetição da resposta do modelo](evidence/2026-11-05-reproducibility.md) (05/11/2026)
- [Qualidade do RAG nos 4 domínios de Agent Skill](evidence/2026-09-rag-multi-domain-quality-validation.md)
- [Qualidade do RAG nas 10 áreas, com modelo gratuito](evidence/2026-11-06-rag-ten-domains.md) (06/11/2026)

Essas evidências registram o sistema na época em que foram feitas, inclusive os papéis de usuário e a lista fechada de domínios, que depois mudaram.
