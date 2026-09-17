# Integração com Provedores de Modelo

## Papel na aplicação

A integração com modelos é uma dependência opcional da camada de planejamento. Ela não substitui o Orquestrador, o catálogo de Agent Skills, os contratos nem o mecanismo de validação.

A aplicação utiliza uma interface interna para evitar que regras de negócio dependam diretamente de um fornecedor. A base atual oferece dois provedores, ambos chamando um serviço real — não há provedor mock:

- `openrouter`: Model Gateway primário, adaptador para a Chat Completions API compatível com múltiplos providers/modelos por trás de uma única credencial (ex.: `nvidia/nemotron-3-super-120b-a12b:free`, `anthropic/claude-sonnet-4.5`);
- `openai`: adaptador direto para a Responses API da OpenAI, mantido como integração opcional para comparação.

A troca entre provedores acontece só por configuração (`LLM_PROVIDER`); nenhuma regra de negócio em `llm_service.py` ou no Orquestrador precisa mudar — essa é a prova prática de que a interface `LLMProvider` é de fato plugável.

Até 25/08/2026 a base tinha um terceiro provedor, `mock`, com resposta determinística e sem chamada externa. Foi removido por decisão explícita: a partir desse ponto, desenvolvimento e testes passaram a validar a integração real com a OpenRouter, usando um modelo gratuito do catálogo (sem custo, sujeito ao limite de 50 requisições/dia sem créditos comprados).

## Configuração padrão

```env
LLM_ENABLED=false
```

Nesse estado, nenhuma chamada externa é realizada — a aplicação sobe normalmente, só a camada de planejamento (e a recuperação de conhecimento RAG, que depende do mesmo provedor para embeddings) fica indisponível.

## Configuração do OpenRouter (provedor primário)

A chave deve ser injetada no backend pelo ambiente de execução ou por um gerenciador de segredos:

```env
LLM_ENABLED=true
LLM_PROVIDER=openrouter
LLM_MODEL=nvidia/nemotron-3-super-120b-a12b:free
LLM_ALLOWED_MODELS=nvidia/nemotron-3-super-120b-a12b:free
OPENROUTER_API_KEY=valor-injetado-fora-do-git
```

Os nomes de modelo do OpenRouter usam o formato `vendor/modelo`. A allowlist (`LLM_ALLOWED_MODELS`) é única e compartilhada entre provedores — ao usar `openrouter`, os valores devem seguir esse formato completo. O modelo padrão acima é gratuito, mas precisa declarar suporte a `structured_outputs` no catálogo da OpenRouter (`GET /api/v1/models`) — nem todo modelo `:free` honra o `response_format` estrito que a aplicação exige; validado empiricamente antes de virar padrão.

A recuperação de conhecimento (RAG) usa o mesmo provedor `openrouter` para gerar embeddings (`openai/text-embedding-3-small` via OpenRouter) — esse modelo de embedding não é gratuito, mas o custo por chamada é irrisório e coberto pelo crédito de teste inicial de qualquer conta nova.

## Configuração da OpenAI (integração direta opcional)

```env
LLM_ENABLED=true
LLM_PROVIDER=openai
LLM_MODEL=gpt-5-mini
LLM_ALLOWED_MODELS=gpt-5-mini,gpt-5
OPENAI_API_KEY=valor-injetado-fora-do-git
```

A aplicação valida se o modelo configurado está na allowlist e impede a inicialização quando a integração está habilitada sem a credencial necessária (própria do provedor selecionado).

A chave não deve ser registrada em:

- `.env.example`;
- frontend;
- banco de dados;
- logs;
- eventos de orquestração;
- documentação;
- prints de validação.

## Fluxo de uma invocação

Uma solicitação só pode ser planejada quando:

- o usuário está autenticado;
- o perfil não é `REVIEWER` (`ORCHESTRATION_ROLES` em `app/core/roles.py` -- desde 2026-09-16, `USER`, `TECHNICIAN` e `ADMIN` podem, só `REVIEWER` fica de fora por separação de funções);
- o token CSRF é válido;
- a solicitação pertence ao usuário, salvo acesso administrativo;
- o estado da solicitação é `QUALIFIED`;
- a integração está habilitada;
- o limite individual ainda não foi atingido.

Antes do envio, o backend:

1. monta a entrada a partir da solicitação;
2. mascara padrões de senha, token, chave e e-mail;
3. aplica o limite de caracteres;
4. calcula o hash da entrada;
5. cria um `LLM Call ID` vinculado ao `Trace ID`;
6. registra o início da invocação.

Após o retorno, o backend:

1. valida a estrutura com Pydantic;
2. calcula o hash da saída;
3. registra status, latência e tokens;
4. registra conclusão ou falha;
5. retorna um plano que exige aprovação humana.

## Endpoints atuais

```text
GET  /api/v1/llm/status
POST /api/v1/llm/requests/{request_id}/plan
GET  /api/v1/llm/invocations/{trace_id}
PATCH /api/v1/admin/users/{user_id}/role
```

O endpoint de status não retorna a chave nem qualquer trecho da credencial.

## Dados registrados

A tabela de invocações mantém metadados técnicos, como:

- solicitação e usuário;
- `Trace ID`;
- `LLM Call ID`;
- provedor e modelo;
- hash da entrada e da saída;
- status;
- latência;
- uso de tokens;
- quantidade de campos mascarados;
- identificadores do provedor, quando disponíveis.

Por padrão, o conteúdo integral não é armazenado:

```env
LLM_STORE_PROVIDER_RESPONSE=false
LLM_STORE_RESULT_CONTENT=false
LLM_LOG_CONTENT=false
LLM_REDACT_SENSITIVE_DATA=true
```

## Cota diária de tokens por usuário

`generate_technical_plan` (`app/services/llm_service.py`) pode opcionalmente recusar chamadas com `429 Too Many Requests` quando a soma de `input_tokens + output_tokens` das invocações `COMPLETED` do usuário no dia corrente (UTC) atinge `LLM_DAILY_TOKEN_LIMIT_PER_USER`. **A partir de 14/09/2026 o padrão é `0` (sem limite)** — a checagem existe mas fica desligada por padrão, para não impor um teto arbitrário à orquestração; quem fizer deploy real e quiser reativar a proteção de custo da conta OpenRouter define um valor positivo nessa variável.

- Contas `ADMIN` são sempre isentas, independentemente do valor configurado.
- A checagem cobre os dois pontos de entrada que acionam o LLM: `POST /llm/requests/{id}/plan` e `POST /agent-skills/requests/{id}/execute` (cada Agent Skill invocada também chama `generate_technical_plan` internamente).
- `GET /llm/status` expõe `daily_token_limit_per_user` e `tokens_used_today` (do usuário autenticado), consumido pela tela de Orquestração para mostrar o uso e desabilitar o botão "Executar orquestração" preventivamente quando a cota já foi atingida (só relevante quando o limite é > 0).
- É uma cota simples de uso (contagem de tokens), não um modelo de negócio de créditos/planos — não há hoje distinção entre usuários "free" e "pro"; ficou registrado como possível evolução futura, não implementada.
- **Histórico**: antes de 14/09/2026 o padrão era 150000, uma conta a partir dos tetos então configurados (`LLM_MAX_INPUT_CHARS=12000` ≈ 3000 tokens, `LLM_MAX_OUTPUT_TOKENS=3000`), não uma calibração de custo real — no pior caso (tudo tratado como tokens de saída do único modelo pago da allowlist, `openai/gpt-5-mini`: $2,00/milhão — [OpenRouter](https://openrouter.ai/openai/gpt-5-mini)) isso custava ~US$0,30/dia por usuário. O teto foi removido (default `0`) a pedido da autora, por estar limitando execuções de orquestração; **quem reativar a cota em produção deve recalibrar o valor**, já que não há mais proteção de custo por padrão.
- **`openai/gpt-5-mini` — correção de 30/08/2026**: as primeiras execuções reais com esse modelo falharam 100% das vezes (`finish_reason: length`, `content: null`). Causa raiz real (reproduzida diretamente contra a API, fora do app): o schema JSON em modo `strict: true` enviado pela aplicação não listava em `required` os campos de `LLMPlan` que têm valor padrão no Pydantic (`required_agents`, `required_skills`, `risks`, `missing_information`, `requires_human_approval`) — o modo estrito da OpenAI exige que **todo** campo de `properties` apareça em `required`, mesmo os que têm default. Um modelo `:free` do OpenRouter tolerava esse schema malformado; o `gpt-5-mini`, roteado direto para infraestrutura da OpenAI/Azure, rejeitava a chamada inteira com HTTP 400 antes de qualquer geração. Corrigido em `app/llm/schemas.py` (`strict_json_schema`), usado pelos dois provedores. Validado com 2 execuções reais consecutivas após a correção, ambas com schema válido e resposta completa.
- Como é uma cota de **tokens**, não de dólares, ela trata modelo grátis e pago da mesma forma -- não é uma proteção calibrada em dinheiro por natureza, funciona mais como um disjuntor contra uso descontrolado (loop, automação com bug) do que como orçamento exato. Se a allowlist um dia incluir um modelo bem mais caro que `gpt-5-mini` e a cota for reativada, essa conta precisa ser refeita.
- **Revisão de 16/09/2026 (Amanda)**: desligar essa cota por padrão deixa um deploy de produção sem nenhuma proteção de custo caso alguém suba direto do `.env.production.example` sem revisar. Corrigido ali: `LLM_DAILY_TOKEN_LIMIT_PER_USER` no template de produção vem com `150000` (não `0`) e um comentário explicando o porquê -- o código continua permitindo `0`, só o template deixou de sugerir isso como padrão seguro.

## Teto de tokens de saída por chamada

`LLM_MAX_OUTPUT_TOKENS` (`app/core/config.py`) controla `max_tokens` (OpenRouter) / `max_output_tokens` (OpenAI) enviado em cada chamada. **A partir de 14/09/2026 o padrão é `0` (sem teto)**: os providers (`app/llm/providers/openrouter_provider.py`, `app/llm/providers/openai_provider.py`) omitem o parâmetro por completo nesse caso, deixando o modelo usar seu próprio máximo. Antes disso o padrão era um valor fixo (1200, depois 3000) que causava respostas vazias (`finish_reason: length`) em modelos de raciocínio como `gpt-5-mini`, que gastam parte do orçamento em "pensamento" interno antes do conteúdo visível — exatamente o tipo de limitação que truncava planos de orquestração. Um valor positivo continua aceito (`>= 128`) para quem quiser reimpor um teto.

- **Impacto em latência (resposta à revisão de 16/09/2026, Amanda)**: medido contra chamadas reais já feitas nos testes desta base com o teto em `0` (modelo `:free` padrão, `nvidia/nemotron-3-super-120b-a12b:free`) -- o tempo de `chat/completions` ficou consistentemente abaixo de 3s por chamada, a maioria abaixo de 1s, sem nenhum caso de estouro do timeout de 45s (`LLM_TIMEOUT_SECONDS`). O motivo: o `response_format` estrito (`json_schema`) já limita o formato da saída a um número finito de campos do `LLMPlan`, então "sem teto" na prática só evita truncar o orçamento de um modelo de raciocínio (como `gpt-5-mini`) gastando parte dele em chain-of-thought interno -- não abre espaço pra geração de prosa livre e ilimitada. Ainda assim, um modelo de raciocínio genuíno sob carga poderia, em teoria, demorar mais; quem notar isso na prática deve reimpor um teto positivo (aceito, `>= 128`) em vez de depender só do timeout.

## Limitações atuais

- A seleção de Agent Skills por domínio já existe (`app/agent_catalog/`), mas é por correspondência exata de domínio (sem roteamento semântico) — decisão deliberada de escopo para uma PoC de desenvolvedora única.
- O plano não executa tools.
- O resultado não é publicado automaticamente.
- O rate limit é local ao processo e precisa de uma solução distribuída antes de escalar horizontalmente.
- A credencial ainda depende de variável de ambiente no desenvolvimento local.
- O modelo gratuito padrão (`nvidia/nemotron-3-super-120b-a12b:free`) tem limite de 50 requisições/dia sem créditos comprados na conta da OpenRouter; a suíte de testes inteira consome uma fração relevante dessa cota a cada execução completa.
- Sem provedor mock, não há mais forma de rodar a suíte de testes nem a aplicação com a integração de modelo habilitada sem uma `OPENROUTER_API_KEY` real.
- O modelo gratuito, sendo compartilhado, apresenta instabilidade ocasional sob rajada de chamadas (rate limit, timeout ou resposta JSON incompleta). `OpenRouterLLMProvider` e `OpenRouterEmbeddingProvider` fazem retry automático (até 2 tentativas, `app/core/retry.py`) para absorver isso; validado empiricamente — sem retry, duas rodadas completas da suíte produziram 1-2 falhas cada (sempre passando isoladamente); com retry, uma rodada completa passou 33/33.
