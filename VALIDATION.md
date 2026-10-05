# Relatório de Validação

Snapshot do estado validado da PoC nesta versão. Não é um substituto das evidências
detalhadas em [`docs/validation/evidence/`](docs/validation/evidence/) — este documento
é o ponto de partida rápido; aquelas, o registro completo por marco/critério.

## Verificações desta versão

- compilação sintática dos módulos Python e checagem de tipos (`mypy`);
- autenticação por sessão opaca, CSRF (double-submit) e bloqueio após tentativas inválidas;
- 4 perfis (`USER`, `TECHNICIAN`, `REVIEWER`, `ADMIN`) e restrição RBAC por endpoint;
- migrations Alembic até `0013_clans`;
- integração real com a OpenRouter (Model Gateway) — **sem provedor mock**: toda
  chamada de LLM nos testes é uma chamada real, com retry para absorver a
  instabilidade conhecida do modelo gratuito compartilhado;
- endpoint seguro de status sem exposição de chave;
- plano estruturado com aprovação humana obrigatória;
- geração de `LLM Call ID` e `Trace ID` para rastreabilidade ponta a ponta;
- hashes SHA-256 da entrada e saída, sem conteúdo integral em `llm_invocations` por padrão;
- redaction de e-mail, senha, token e padrões de chave antes de qualquer chamada externa;
- cota diária de tokens por usuário não-administrador;
- catálogo de Agent Skills: 4 skills oficiais (executores dedicados) + skills criadas
  por usuário (executor genérico guiado por persona) — nascem `OFFICIAL` (visíveis a
  qualquer usuário autenticado) por padrão, com opção de `PRIVATE` restrita ao dono/admin
  ou `CLAN` restrita aos membros de um clã;
- clãs: grupos auto-serviço, qualquer usuário cria e gerencia membros;
- login com GitHub (OAuth, opcional) além de e-mail/senha;
- anexo de documentos de texto como contexto adicional de uma solicitação;
- pipeline RAG com qualidade medida (Precision@k/Recall@k/MRR) nos 4 domínios originais
  de Agent Skill, com bases de conhecimento co-indexadas (ver evidências específicas) —
  catálogo hoje tem 10 domínios ao todo (ver seção "Núcleo comum de engenharia");
- 112 testes automatizados do backend, 100% reais (sem mock).

## Núcleo comum de engenharia

Itens exigidos pela rubrica independentemente da trilha (IA vs. Web Apps):

- [x] **CI/CD** — `.github/workflows/ci.yml`, roda em todo push/PR.
- [x] **Análise estática no pipeline** — `ruff check` + `mypy` (backend) e `tsc` (frontend),
  como etapas do mesmo workflow de CI.
- [ ] **Wiki no GitHub** — ainda não criada.
- [ ] **Monitoramento/observabilidade** — ainda não implementado.

A suíte de testes fica fora do CI de propósito: chama a OpenRouter de verdade, sem mock
(ver seção "Testes" abaixo) — rodar a cada push gastaria créditos reais e poderia ficar
vermelho por instabilidade do provedor gratuito, não por bug de código. Continua rodando
localmente antes de cada PR.

## Comandos locais

```powershell
docker compose up --build -d
docker compose exec backend alembic current
docker compose ps
```

Resultado esperado do `alembic current`:

```text
0013_clans (head)
```

## Testes

Não existe provedor mock: rodar a suíte exige uma `OPENROUTER_API_KEY` real no ambiente.

```powershell
docker run --rm `
  --mount "type=bind,source=$((Get-Location).Path)\backend,target=/app" `
  --env-file .env `
  -w /app `
  python:3.12-slim `
  sh -c "pip install --no-cache-dir -r requirements-dev.txt && pytest -v"
```

Uma ou duas falhas isoladas por execução completa, sempre passando ao rodar a
mesma prova isoladamente de novo, são a instabilidade já documentada do modelo
gratuito compartilhado (ver [`docs/integrations/model-provider.md`](docs/integrations/model-provider.md))
— não uma regressão.

## Evidências detalhadas

- [Validação da fundação](docs/validation/evidence/2026-08-foundation-validation.md)
- [Extensibilidade plug-and-play](docs/validation/evidence/2026-08-plug-and-play-extensibility.md)
- [Medição de KPIs (M7)](docs/validation/evidence/2026-08-m7-kpi-measurement.md)
- [Qualidade do RAG (domínio Código Legado)](docs/validation/evidence/2026-08-30-rag-quality-validation.md)
- [Qualidade do RAG nos 4 domínios de Agent Skill](docs/validation/evidence/2026-09-rag-multi-domain-quality-validation.md)
