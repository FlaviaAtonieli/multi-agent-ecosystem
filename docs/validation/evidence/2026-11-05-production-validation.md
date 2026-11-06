# Validação em produção, 05/11/2026

Conferência dos requisitos do portfólio com o site ligado no Azure e o SonarCloud ativo, logo depois do merge dos PRs #101 a #105. Os horários dos registros estão em UTC (06/11, 00h20 a 00h40), que corresponde à noite de 05/11 no horário de Brasília.

Ambiente: https://jolly-grass-0a3af3f10.2.azurestaticapps.net, commit `d009c8b` no `main`.

## Como foi feito

- Os testes rodaram no site público, com o Chrome controlado pelo Playwright. Alguns passos foram feitos direto pela API, com a mesma sessão.
- A conta de teste foi criada pelo cadastro normal: `teste-claude-11052125@example.com`.
- Ela usou um clã fechado próprio, **Teste Claude**, com a skill oficial Código Legado. Nenhum clã de outra pessoa foi usado.
- A IA rodou só com o modelo gratuito `dots-studio/dots-3-note-preview:free`, que está na lista de modelos permitidos em produção. No total foram 2 orquestrações.

## Versão no ar

| Conferência | Resultado |
|---|---|
| Rota nova `POST /agent-skills/requests/{id}/cancel` | 401 sem sessão. Uma rota inexistente dá 404, então a versão nova está no ar |
| Migração do banco | O backend subiu, e o contêiner roda `alembic upgrade head` antes de iniciar |
| CI no `main` | CI, Publish images e Azure Static Web Apps verdes |

## Segurança e entrega

| Conferência | Resultado |
|---|---|
| HTTP para HTTPS | 301 |
| Cabeçalhos do site | HSTS com preload, CSP restrita (`script-src 'self'`, `frame-ancestors 'none'`), `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy` |
| Cabeçalhos da API | HSTS, `nosniff`, `X-Frame-Options: DENY` e `X-Request-ID` em cada resposta |
| Cache | `index.html` com `no-cache`. Arquivos de `/assets/` com `max-age=31536000, immutable` |

## SonarCloud (`main`, análise de 06/11 00:22 UTC)

| Métrica | Valor |
|---|---|
| Quality gate | **OK** |
| Bugs, vulnerabilidades, code smells | 0, 0, 0 |
| Notas de confiabilidade, segurança e manutenibilidade | A, A, A |
| Security hotspots revisados | 100% |
| Duplicação | 1,3% |
| Linhas de código | 26.825 |

Os 5 avisos de senha em `openapi_examples.py` (regra S2068) foram marcados como falso positivo. São senhas fictícias usadas como exemplo na documentação Swagger.

O SonarCloud não mostra cobertura, porque a análise automática não importa esse relatório. A cobertura é exigida pelo CI: no `main`, ficou em **85,89% no backend** (mínimo de 75%) e **56,53% de linhas no frontend** (mínimo de 25%).

## Fluxos de negócio

| Passo | Resultado |
|---|---|
| Cadastro de conta nova | ✅ 201 |
| Login com senha pela tela | ✅ chega ao painel |
| Criar clã e adicionar skill oficial | ✅ (pela API) |
| Clã sem skills ativas | ✅ a solicitação é recusada com "Este clã ainda não tem Agent Skills ativas" |
| Contexto "TESTE " ×12 | ✅ fica em Aguardando contexto, mostra os motivos e não oferece Executar |
| Complementar com teclado batido | ✅ continua barrado, com "O contexto ainda não é suficiente" |
| Complementar com contexto real | ✅ qualifica e libera Executar |
| Executar e interromper | ✅ Cancelada em 11 s, com `ORCHESTRATION_CANCELLED` na linha do tempo |
| Complementar e executar de novo | ✅ terminou em 71 s em Validando (revisão humana) |
| Revisão humana (aprovar) | ✅ Concluída |
| Ajuda (!) da auditoria | ✅ 5 passos, fecha no fim, sem violações do axe (WCAG 2.1 AA) |
| Erros de página ou 5xx em toda a jornada | nenhum |

Não foram conferidos em produção: código por e-mail, recuperação de senha e exclusão de conta, que dependem de uma caixa de e-mail real ou apagam a conta de teste; perguntas de acompanhamento, que seriam mais uma chamada de IA; importar skill e sugestões.

## A orquestração com IA

Trace `TRC-20261106-7CCE71`.

| Etapa | Registro |
|---|---|
| RAG | 3 trechos recuperados (top_k 3) em 5.896 ms |
| Modelo | `dots-studio/dots-3-note-preview:free`, conforme o evento `LLM_INVOCATION_STARTED` |
| Chamada | 912 tokens de entrada e 2.483 de saída, em 39.198 ms |
| Skill | Código Legado, com confiança MÉDIO e 65.647 ms ao todo |
| Quality Gate | aprovado, mas pediu revisão humana por causa da confiança MÉDIO |
| Arquivos gerados | **0** |

O que isso mostra:

- O caminho completo funciona em produção, com o rastro de cada etapa: qualificação, RAG, modelo, contrato MCP, Quality Gate, consolidação e revisão humana.
- **O modelo gratuito não gerou arquivos.** O recurso de arquivos e ZIP (#98) continua sem ter sido visto funcionando com um modelo real. Não dá para concluir se o motivo é o modelo ou o prompt.
- A síntese ficou rasa, mas a solicitação de teste também era rasa ("validar a barreira de contexto"). Isso não mede a qualidade da resposta.
- A busca no RAG levou quase 6 s, a maior parte na chamada de embeddings ao provedor externo.

## O que continua pendente

- **Deploy automático do backend.** O único segredo do repositório é o token do Static Web App. Sem o `AZURE_BACKEND_DEPLOY_WEBHOOK`, a imagem é publicada, mas o App Service precisa de `az webapp restart` manual.
- **Monitoramento em produção.** O linked backend do Static Web App bloqueia o acesso direto ao App Service, e isso inclui `/metrics` ([monitoring.md](../../deployment/monitoring.md)).
- **Wiki.** A última atualização é de 03/11/2026. Faltam Swagger, interromper a execução, a barreira de contexto, o cache de embeddings e os parâmetros fixos do modelo.

Dados deixados em produção: a conta de teste, o clã Teste Claude e a solicitação `TRC-20261106-7CCE71`.
