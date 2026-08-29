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
- o perfil é `TECHNICIAN` ou `ADMIN`;
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

Para proteger a assinatura/créditos da conta OpenRouter contra o consumo de um único usuário, `generate_technical_plan` (`app/services/llm_service.py`) verifica, antes de qualquer chamada ao provedor, a soma de `input_tokens + output_tokens` das invocações `COMPLETED` do usuário no dia corrente (UTC). Se o total já atingiu `LLM_DAILY_TOKEN_LIMIT_PER_USER` (padrão: 150000, `0` desabilita), a chamada é recusada com `429 Too Many Requests` antes de gastar créditos.

- Contas `ADMIN` são isentas (operador confiável da assinatura).
- A checagem cobre os dois pontos de entrada que acionam o LLM: `POST /llm/requests/{id}/plan` e `POST /agent-skills/requests/{id}/execute` (cada Agent Skill invocada também chama `generate_technical_plan` internamente).
- `GET /llm/status` expõe `daily_token_limit_per_user` e `tokens_used_today` (do usuário autenticado), consumido pela tela de Orquestração para mostrar o uso e desabilitar o botão "Executar orquestração" preventivamente quando a cota já foi atingida.
- É uma cota simples de uso (contagem de tokens), não um modelo de negócio de créditos/planos — não há hoje distinção entre usuários "free" e "pro"; ficou registrado como possível evolução futura, não implementada.

## Limitações atuais

- A seleção de Agent Skills por domínio já existe (`app/agent_catalog/`), mas é por correspondência exata de domínio (sem roteamento semântico) — decisão deliberada de escopo para uma PoC de desenvolvedora única.
- O plano não executa tools.
- O resultado não é publicado automaticamente.
- O rate limit é local ao processo e precisa de uma solução distribuída antes de escalar horizontalmente.
- A credencial ainda depende de variável de ambiente no desenvolvimento local.
- O modelo gratuito padrão (`nvidia/nemotron-3-super-120b-a12b:free`) tem limite de 50 requisições/dia sem créditos comprados na conta da OpenRouter; a suíte de testes inteira consome uma fração relevante dessa cota a cada execução completa.
- Sem provedor mock, não há mais forma de rodar a suíte de testes nem a aplicação com a integração de modelo habilitada sem uma `OPENROUTER_API_KEY` real.
- O modelo gratuito, sendo compartilhado, apresenta instabilidade ocasional sob rajada de chamadas (rate limit, timeout ou resposta JSON incompleta). `OpenRouterLLMProvider` e `OpenRouterEmbeddingProvider` fazem retry automático (até 2 tentativas, `app/core/retry.py`) para absorver isso; validado empiricamente — sem retry, duas rodadas completas da suíte produziram 1-2 falhas cada (sempre passando isoladamente); com retry, uma rodada completa passou 33/33.
