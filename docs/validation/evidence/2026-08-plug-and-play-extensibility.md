# Evidência de Validação - Extensibilidade Plug-and-Play

**Consolidação documental:** 25/08/2026
**Escopo:** RFC seção 5.4 (sétima etapa) e seção 5.5 (critério mínimo 7) — acoplamento de uma nova Agent Skill sem alteração do núcleo do Orquestrador (RF05, RNF01)

## O que foi testado

Uma quarta Agent Skill, inédita — **Segurança da Informação** (`seguranca_informacao`) — foi criada e acoplada ao ecossistema depois que as três skills originais (Código Legado, Regras de Negócio, Arquitetura de Software) já estavam implementadas e com testes passando. O objetivo foi verificar se o Orquestrador reconhece e aciona a nova skill sem alteração direta no seu núcleo, conforme exigido por RF05 ("O sistema deve permitir que novas Agent Skills sejam acopladas ao ecossistema sem exigir alteração direta no núcleo da aplicação, desde que respeitem os contratos técnicos previamente definidos").

## O que foi adicionado

| Arquivo | Natureza |
|---|---|
| `app/agent_catalog/tool_interface.py` — `SecuritySkillExecutor` | Nova classe, mesmo padrão das outras três |
| `app/agent_catalog/mcp_servers/security_server.py` | Novo servidor MCP, mesmo padrão dos outros três |
| `app/agent_manifest/fixtures/security-skill.md` | Novo manifesto de exemplo |
| `app/agent_manifest/manifest.py` — `DomainLiteral` | +1 entrada (`seguranca_informacao`) — camada de contratos, não núcleo do Orquestrador |
| `app/agent_catalog/mcp_client.py` — `_DOMAIN_SERVER_MODULES` | +1 linha (mapeamento domínio → servidor) — ponto de registro explícito, não lógica de orquestração |
| `app/agent_catalog/tool_interface.py` — `AgenteEmissor.dominio` | +1 valor no `Literal` — mesmo motivo acima |

## O que **não** foi tocado

Verificado por `git diff --stat` sobre os arquivos que implementam a lógica de seleção, execução e consolidação do Orquestrador — diff vazio nos três:

- `app/services/agent_skill_orchestration_service.py` (seleção de skills por domínio, invocação MCP, consolidação da resposta final)
- `app/services/orchestration_service.py` (máquina de estados da solicitação técnica)
- `app/quality_gate/service.py` (avaliação cruzada das respostas parciais)
- `app/agent_catalog/registry.py` (registro e consulta do catálogo de Agent Skills)

Nenhuma dessas quatro peças — que juntas implementam o "núcleo" descrito em RF05 — precisou de qualquer mudança para que a nova skill funcionasse. Isso acontece porque a seleção (`select_skills_for_domain`), a invocação (`call_skill_tool`) e a consolidação já operavam de forma genérica sobre "as skills selecionadas para o(s) domínio(s) da solicitação", independentemente de quantos domínios existem ou de quais são.

## Teste automatizado

`backend/tests/test_agent_skills.py::test_new_agent_skill_couples_without_orchestrator_changes`:

1. Importa o manifesto da nova skill pela mesma API genérica (`POST /api/v1/agent-skills/import`) usada pelas outras três — nenhum código especial para o novo domínio.
2. Cria uma solicitação técnica com `requested_domains=["seguranca_informacao"]`.
3. Executa a orquestração (`POST /api/v1/agent-skills/requests/{id}/execute`) e verifica que a skill foi selecionada, invocada via MCP, avaliada pelo Quality Gate e consolidada na resposta final — o mesmo fluxo de ponta a ponta das demais.

## Resultado

```text
pytest -q
33 passed
```

`ruff check app tests`: 0 findings. `mypy app`: 0 issues (84 arquivos). `tsc -b` (frontend): sem erros.

## Limitações deste registro

- A prova cobre o caso onde o novo domínio já é conhecido pelo tipo `DomainLiteral`; a arquitetura não aceita hoje um domínio arbitrário em tempo de execução sem essa entrada — decisão de escopo documentada em `docs/integrations/model-provider.md`.
- Este documento não substitui a medição formal dos KPIs do RFC (seção 5.5), que fica para o marco M7 (Validação e Avaliação).
