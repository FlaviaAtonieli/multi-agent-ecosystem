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
- Rate limit em cadastro, login, renovação e chamadas de modelo.

### Proteção contra enumeração e força bruta

- Mensagem genérica para usuário inexistente ou senha incorreta.
- Verificação fictícia de senha quando o e-mail não existe, reduzindo diferenças de tempo.
- Bloqueio temporário após tentativas consecutivas inválidas.

### Autorização

A implementação atual possui três perfis:

| Perfil | Permissões principais |
|---|---|
| `USER` | Funções gerais e solicitações próprias |
| `TECHNICIAN` | Planejamento em solicitações próprias e consulta dos próprios rastros |
| `ADMIN` | Administração de usuários, perfis e consultas administrativas |

A promoção de perfil é restrita ao administrador. Quando o papel de outro usuário é alterado, as sessões desse usuário são revogadas.

O perfil `REVIEWER`, previsto na evolução da PoC, ainda não faz parte da implementação atual.

## Segurança da integração com modelos

- Integração desabilitada por padrão.
- Chave disponível somente no backend.
- Modelo validado por allowlist.
- Execução limitada a `TECHNICIAN` e `ADMIN`.
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

Configuração mínima esperada:

```env
ENVIRONMENT=production
COOKIE_SECURE=true
ALLOW_REGISTRATION=false
AUTO_CREATE_TABLES=false
```

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
