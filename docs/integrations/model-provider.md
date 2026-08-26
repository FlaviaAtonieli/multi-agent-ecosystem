# Integração com Provedores de Modelo

## Papel na aplicação

A integração com modelos é uma dependência opcional da camada de planejamento. Ela não substitui o Orquestrador, o catálogo de Agent Skills, os contratos nem o mecanismo de validação.

A aplicação utiliza uma interface interna para evitar que regras de negócio dependam diretamente de um fornecedor. A base atual oferece três provedores:

- `mock`: resposta determinística para desenvolvimento e testes;
- `openrouter`: Model Gateway primário, adaptador para a Chat Completions API compatível com múltiplos providers/modelos por trás de uma única credencial (ex.: `openai/gpt-5-mini`, `anthropic/claude-sonnet-4.5`), desabilitado por padrão;
- `openai`: adaptador direto para a Responses API da OpenAI, mantido como integração opcional para comparação.

A troca entre provedores acontece só por configuração (`LLM_PROVIDER`); nenhuma regra de negócio em `llm_service.py` ou no Orquestrador precisa mudar — essa é a prova prática de que a interface `LLMProvider` é de fato plugável.

## Configuração padrão

```env
LLM_ENABLED=false
LLM_PROVIDER=mock
OPENAI_API_KEY=
```

Nesse estado, nenhuma chamada externa é realizada.

Para testar a integração sem chave:

```env
LLM_ENABLED=true
LLM_PROVIDER=mock
```

O provedor simulado gera um plano estruturado e permite validar autorização, rastreabilidade e persistência sem consumo externo.

## Configuração futura do OpenRouter (provedor primário)

A chave deve ser injetada no backend pelo ambiente de execução ou por um gerenciador de segredos:

```env
LLM_ENABLED=true
LLM_PROVIDER=openrouter
LLM_MODEL=openai/gpt-5-mini
LLM_ALLOWED_MODELS=openai/gpt-5-mini,anthropic/claude-sonnet-4.5
OPENROUTER_API_KEY=valor-injetado-fora-do-git
```

Os nomes de modelo do OpenRouter usam o formato `vendor/modelo`. A allowlist (`LLM_ALLOWED_MODELS`) é única e compartilhada entre provedores — ao usar `openrouter`, os valores devem seguir esse formato completo.

## Configuração futura da OpenAI (integração direta opcional)

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

## Limitações atuais

- O perfil `REVIEWER` previsto no desenho acadêmico ainda não foi implementado.
- A seleção de Agent Skills por domínio já existe (`app/agent_catalog/`), mas é por correspondência exata de domínio (sem roteamento semântico) — decisão deliberada de escopo para uma PoC de desenvolvedora única.
- O plano não executa tools.
- O resultado não é publicado automaticamente.
- O rate limit é local ao processo e precisa de uma solução distribuída antes de escalar horizontalmente.
- A credencial ainda depende de variável de ambiente no desenvolvimento local.
