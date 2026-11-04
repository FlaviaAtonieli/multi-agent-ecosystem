# Relatório de Validação

Snapshot do estado validado da PoC nesta versão. Não é um substituto das evidências
detalhadas em [`docs/validation/evidence/`](docs/validation/evidence/) — este documento
é o ponto de partida rápido; aquelas, o registro completo por marco/critério.

## Verificações desta versão

- `ruff` e `mypy` no backend; `tsc` e build no frontend;
- autenticação por sessão opaca, CSRF (double-submit) e bloqueio após tentativas inválidas;
- login com GitHub e Google (OAuth, opcionais), código por e-mail em navegador novo e
  recuperação de senha por e-mail;
- sem papéis de usuário desde 14/10/2026: o acesso é controlado por propriedade,
  visibilidade da skill e cota de tokens (ver [`SECURITY.md`](SECURITY.md#autorização));
- migrations Alembic até `0018_password_reset`;
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
- pipeline RAG com qualidade medida (Precision@k, Recall@k e MRR) em 4 das 10 áreas
  oficiais (ver [`docs/ai-pipeline.md`](docs/ai-pipeline.md));
- métricas de IA, execução e autenticação em `/metrics`, com painel e alertas no Grafana.

## Testes e cobertura

Conferidos em todo push e PR pelo CI, que falha abaixo das metas:

| Parte | Ferramenta | Testes (03/11/2026) | Cobertura de linhas | Meta |
|---|---|---:|---:|---:|
| Backend | pytest | 152 | 80% | 75% |
| Frontend | Vitest e Testing Library | 99 | 48% | 25% |

A contagem do backend não inclui os 26 testes marcados com `llm`, que chamam a OpenRouter
de verdade e ficam fora do CI: rodar a cada push gastaria créditos reais e poderia ficar
vermelho por instabilidade do provedor, não por bug de código. **Eles ainda não foram
executados com o modelo padrão atual (`openai/gpt-5-mini`).**

Os testes do frontend simulam só a rede. O restante do código roda de verdade.

Para rodar, veja a seção "Testes" do [README](README.md#testes).

## Núcleo comum de engenharia

Itens exigidos pela rubrica independentemente da linha de projeto:

- [x] **CI/CD** — [`ci.yml`](.github/workflows/ci.yml) em todo push e PR, e [`publish-images.yml`](.github/workflows/publish-images.yml) com o [deploy do backend](docs/deployment/azure.md#9-deploy-automático-do-backend). O frontend é publicado pelo workflow do Static Web Apps.
- [x] **Wiki no GitHub** — [wiki do repositório](https://github.com/FlaviaAtonieli/multi-agent-ecosystem/wiki).
- [ ] **Análise estática de código e segurança** — `ruff`, `mypy` e `tsc` rodam no CI. **Falta** a análise de segurança.
- [ ] **Monitoramento** — Prometheus, Grafana, painel e alertas estão [prontos](docs/monitoring.md) e foram testados contra um backend local. **Falta** ligar a leitura do backend em produção.

## Comandos locais

```powershell
docker compose up --build -d
docker compose exec backend alembic current
docker compose ps
```

Resultado esperado do `alembic current`:

```text
0018_password_reset (head)
```

## Evidências detalhadas

- [Validação da fundação](docs/validation/evidence/2026-08-foundation-validation.md)
- [Extensibilidade plug-and-play](docs/validation/evidence/2026-08-plug-and-play-extensibility.md)
- [Medição de KPIs (M7)](docs/validation/evidence/2026-08-m7-kpi-measurement.md) — com modelo gratuito e execução em sequência; ainda não repetida com o código atual
- [Qualidade do RAG (domínio Código Legado)](docs/validation/evidence/2026-08-30-rag-quality-validation.md)
- [Qualidade do RAG nos 4 domínios de Agent Skill](docs/validation/evidence/2026-09-rag-multi-domain-quality-validation.md)

Essas evidências registram o sistema na época em que foram feitas, inclusive os papéis de usuário e a lista fechada de domínios, que depois mudaram.
