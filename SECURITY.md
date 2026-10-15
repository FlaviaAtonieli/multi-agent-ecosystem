# Segurança

Este documento registra os controles implementados na PoC, as limitações conhecidas e os requisitos adicionais para um ambiente de produção.

## Controles implementados

### Autenticação e sessão

- Senhas protegidas com Argon2 por meio de `pwdlib`.
- Sessões opacas geradas com 48 bytes aleatórios.
- Persistência apenas do hash SHA-256 do token de sessão.
- Cookie de sessão `HttpOnly` e `SameSite=Lax`.
- Flag `Secure` configurável para uso obrigatório com HTTPS.
- Revogação da sessão atual ou de todas as sessões do usuário.
- Limite configurável de sessões ativas.

A aplicação utiliza sessão persistida no servidor, e não JWT armazenado no navegador. A escolha facilita revogação, logout global e controle de sessões na primeira versão.

### Proteção das requisições

- CSRF pelo padrão double-submit, vinculado à sessão autenticada.
- CORS explícito.
- Lista de hosts confiáveis.
- Cabeçalhos de segurança aplicados pelo middleware.
- Identificador de requisição para correlação de erros.
- Rate limit em cadastro, login, renovação e chamadas de modelo. Contabilizado pelo IP direto da conexão por padrão; atrás de um reverse proxy real, `TRUSTED_PROXY_IPS` permite confiar no cabeçalho `X-Forwarded-For` — só quando o IP que abriu a conexão for o próprio proxy configurado, para não ser possível forjar o cabeçalho contornando o limite.
- `/docs`, `/redoc` e `/openapi.json` desligados quando `ENVIRONMENT=production`, independente de a porta do backend estar ou não acessível diretamente do host.

### Proteção contra enumeração e força bruta

- Mensagem genérica para usuário inexistente ou senha incorreta.
- Verificação fictícia de senha quando o e-mail não existe, reduzindo diferenças de tempo.
- Bloqueio temporário após tentativas consecutivas inválidas.

### Autorização

Desde 14/10/2026 não há papéis de usuário (os antigos `USER`, `TECHNICIAN`, `REVIEWER` e `ADMIN` foram removidos para simplificar o uso, migração `0016_drop_user_roles`). Todo usuário autenticado tem as mesmas permissões, e o controle de acesso passa a ser por **propriedade**:

| Recurso | Quem pode |
|---|---|
| Solicitações, orquestrações e revisão humana | Só quem abriu a solicitação (lookup owner-scoped, 404 para os demais) |
| Trilha de auditoria | Cada usuário vê apenas os eventos das próprias solicitações |
| Agent Skills | Qualquer usuário cria ou importa, inclusive `OFFICIAL`; editar, desativar e reativar fica com quem criou (numa skill `CLAN`, também com o dono do clã) |
| Clãs | Regras por clã (`is_open`, `skills_policy`, `members_policy`); o dono (`created_by_id`) altera as configurações |

Não há mais painel de administração: desativar a conta de outro usuário deixou de existir pela interface.

### Três camadas de controle de acesso

Independentes entre si e avaliadas nesta ordem -- cada uma só é checada se a anterior já passou:

1. **Propriedade** (controla *sobre o que* a pessoa age). Toda solicitação, orquestração e revisão é do usuário que a criou.
2. **Visibilidade da Agent Skill** (controla *o que* existe pra executar). `OFFICIAL` é visível a qualquer usuário autenticado; `PRIVATE` fica restrita ao dono; `CLAN` fica restrita aos membros do clã (`clan_id`) associado.
3. **Cota diária de tokens** (controla *quanto* cada pessoa pode executar naquele dia; desligada por padrão -- `LLM_DAILY_TOKEN_LIMIT_PER_USER=0`). Vale para todas as contas. Detalhes: [docs/integrations/model-provider.md](docs/integrations/model-provider.md#cota-diária-de-tokens-por-usuário).

> Como o cadastro é aberto por padrão (`ALLOW_REGISTRATION=true`) e todo usuário executa orquestrações e publica skills `OFFICIAL`, um deploy exposto publicamente deve considerar reativar a cota diária de tokens (item 3) e/ou fechar o cadastro.

## Segurança da integração com modelos

- Integração desabilitada por padrão.
- Chave disponível somente no backend.
- Modelo validado por allowlist.
- Execução liberada a qualquer usuário autenticado, sobre as próprias solicitações.
- Verificação de propriedade da solicitação.
- Limite de caracteres antes do envio.
- Mascaramento de padrões de senha, token, chave e e-mail.
- `Trace ID` para o fluxo e `LLM Call ID` para cada invocação.
- Persistência de hashes, status, tokens e latência.
- Armazenamento do conteúdo integral desabilitado por padrão.
- Resposta estruturada validada por Pydantic.
- Aprovação humana obrigatória.
- Nenhuma execução automática de tools ou publicação.

O endpoint de status não retorna a chave nem informa parte de seu valor.

## Segurança das Agent Skills

A implementação do catálogo deve respeitar estas regras:

- manifesto obrigatório;
- domínio e responsabilidade definidos;
- contratos de entrada e saída validados;
- versionamento;
- limites de atuação;
- executor presente em allowlist;
- bloqueio de upload e execução arbitrária de código;
- registro de criação, validação, habilitação e desabilitação;
- atuação read-only na PoC.

Uma Agent Skill não deve ser habilitada apenas porque o arquivo foi recebido. O registro depende de validação estrutural e autorização.

## Dados e auditoria

A auditoria registra eventos operacionais sem armazenar senha, token de sessão ou chave de provedor.

Para a PoC:

- artefatos devem ser sintéticos, públicos ou anonimizados;
- credenciais e dados pessoais desnecessários devem ser bloqueados ou mascarados;
- cada execução deve permanecer vinculada ao `Trace ID`;
- conteúdo sensível não deve ser incluído em prints ou evidências acadêmicas;
- retenção e exclusão devem ser definidas antes da validação com usuários externos.

## Limitações conhecidas

Antes de uso real em produção, ainda precisam ser avaliados ou implementados:

- confirmação de e-mail;
- recuperação segura de senha;
- autenticação multifator;
- OAuth 2.0 ou OpenID Connect corporativo;
- rate limit distribuído em Redis;
- gerenciador de segredos;
- rotação formal de credenciais;
- política de retenção de logs e dados funcionais;
- detecção mais ampla de dados sensíveis;
- análise de arquivos enviados;
- proteção específica contra prompt injection;
- monitoramento e alertas;
- testes de invasão;
- revisão de dependências e imagens Docker;
- processo formal de resposta a incidentes;
- revisão jurídica e de LGPD.

## Requisitos de produção

Configuração mínima esperada — use `.env.production.example` como ponto de partida:

```env
ENVIRONMENT=production
COOKIE_SECURE=true
ALLOW_REGISTRATION=false
AUTO_CREATE_TABLES=false
```

`ENVIRONMENT=production` com `COOKIE_SECURE=false` não é apenas desaconselhado: a aplicação recusa iniciar nessa combinação (`Settings.validate_production_hardening`, `app/core/config.py`) — os cookies de sessão e CSRF trafegariam sem a flag `Secure`, que depende de HTTPS de verdade na frente da aplicação para ter efeito.

O ambiente também deve utilizar:

- HTTPS;
- domínio real;
- CORS restrito;
- credenciais distintas para banco e administrador;
- segredo injetado fora do Git;
- backup do PostgreSQL;
- logs com acesso controlado;
- atualização automatizada das dependências;
- pipeline de testes e análise estática.

O arquivo `.env` é adequado apenas ao desenvolvimento local e deve permanecer ignorado pelo Git.
