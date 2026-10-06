# Login com Google

## Papel na aplicação

Método de autenticação **adicional**, ao lado do fluxo de e-mail/senha e do login com GitHub (ver [docs/integrations/github-oauth.md](github-oauth.md)) -- não substitui nenhum dos dois. Uma conta pode ser criada por e-mail/senha (`password_hash` preenchido), por GitHub (`github_id` preenchido) ou por Google (`google_id` preenchido); hoje não existe fluxo pra vincular duas dessas formas numa mesma conta depois de criadas separadamente.

Desabilitado por padrão (`GOOGLE_OAUTH_ENABLED=false`): o projeto sobe normalmente sem nenhuma credencial do Google configurada e `/api/v1/auth/google/*` responde `404`. O botão "Continuar com Google" no frontend não checa esse estado (mesmo comportamento pré-existente do botão do GitHub) -- ele aparece sempre; clicar nele sem a integração habilitada leva a um `404` cru em vez de um redirect amigável. Gap conhecido, não corrigido aqui.

## Criando o OAuth Client no Google Cloud Console

Cada ambiente (dev local, produção) deve ter seu próprio OAuth Client -- não reaproveite credenciais entre eles.

1. Acesse [console.cloud.google.com](https://console.cloud.google.com/), crie (ou selecione) um projeto.
2. **APIs e Serviços → Tela de permissão OAuth**: configure o básico (nome do app, e-mail de suporte). Tipo "Externo" funciona pra desenvolvimento/demo; usuários de teste precisam ser adicionados explicitamente enquanto o app estiver em modo de teste.
3. **APIs e Serviços → Credenciais → Criar credenciais → ID do cliente OAuth**:
   - **Tipo de aplicativo**: "Aplicativo da Web".
   - **Nome**: qualquer nome identificável (ex.: `Flav.IA (dev local)`).
   - **URIs de redirecionamento autorizados**: precisa bater **exatamente** com `GOOGLE_OAUTH_REDIRECT_URI` do `.env` -- por padrão, `http://localhost:8000/api/v1/auth/google/callback`.
4. Clique em **Criar**. Copie o **Client ID** e o **Client secret** mostrados.
5. Preencha no `.env` (raiz do projeto, ou `backend/.env` se rodando o backend fora do Docker):

   ```env
   GOOGLE_OAUTH_ENABLED=true
   GOOGLE_CLIENT_ID=<Client ID copiado>
   GOOGLE_CLIENT_SECRET=<Client secret copiado>
   GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
   FRONTEND_BASE_URL=http://localhost:3000
   ```

6. Reinicie o backend. O botão "Continuar com Google" passa a aparecer nas telas de login e cadastro.

Pra produção, repita o processo com um OAuth Client separado apontando pro domínio real (`https://seu-dominio.com/api/v1/auth/google/callback`), e preencha as mesmas variáveis em `.env.production.example`/no gerenciador de segredos do deploy. Também é preciso publicar a tela de permissão OAuth (sair do modo de teste) pra qualquer conta Google poder entrar, não só usuários de teste cadastrados manualmente.

## Fluxo (authorization code, OpenID Connect)

```text
Usuário clica "Continuar com Google"
  -> navegador GET /api/v1/auth/google/login
  -> backend gera `state` aleatório, grava num cookie curto (10 min) e redireciona pro Google
  -> usuário autoriza no Google
  -> Google redireciona o navegador pra /api/v1/auth/google/callback?code=...&state=...
  -> backend valida o `state` contra o cookie (proteção CSRF própria do OAuth --
     distinta do CSRF da sessão, que não se aplica aqui por ser navegação de página inteira)
  -> troca o `code` por um access_token (chamada servidor-a-servidor com o client_secret)
  -> busca o perfil (endpoint userinfo do OpenID Connect) e confirma e-mail verificado
  -> encontra ou cria a conta, abre sessão normal (mesmos cookies de sempre)
  -> redireciona pro frontend (FRONTEND_BASE_URL/dashboard, ou /login?error=... em caso de falha)
```

## Resolução de conta (`find_or_create_user`, `app/services/google_oauth_service.py`)

Mesma lógica do GitHub (ver [docs/integrations/github-oauth.md](github-oauth.md)), trocando `github_id` por `google_id` (o claim `sub` do perfil OpenID Connect):

1. **Por `google_id`** primeiro (estável mesmo que o usuário troque de e-mail ou nome no Google) -- se existe, entra nessa conta e atualiza nome/avatar.
2. Se não existe por `google_id`, verifica **por e-mail**. Se já existe uma conta (de e-mail/senha, de GitHub ou de outro `google_id`) com esse e-mail, a request é recusada com um erro claro (`google_email_in_use`) -- **não há auto-link silencioso por e-mail**, pela mesma razão de account-takeover documentada pro GitHub.
3. Só então cria uma conta nova, papel `USER`, sem senha (`password_hash=None`), respeitando `ALLOW_REGISTRATION`.

## Erros expostos ao frontend

O callback sempre redireciona (nunca deixa uma tela de erro JSON crua no navegador). `/login?error=<código>`:

| código | motivo |
|---|---|
| `google_oauth_failed` | `state` ausente/não bate (possível CSRF ou cookie expirado), e-mail não verificado, ou qualquer falha na troca de código/consulta de perfil com o Google |
| `google_email_in_use` | o e-mail verificado do Google já pertence a outra conta |
| `account_inactive` | a conta (já existente) está desativada pelo admin |

## Login por senha numa conta Google-only

Uma conta criada via Google não tem `password_hash`. `POST /auth/login` com e-mail/senha pra essa conta retorna `401` com uma mensagem indicando pra usar o botão do Google -- `authenticate_user` (`app/services/auth_service.py`) escolhe o rótulo certo ("GitHub" ou "Google") verificando qual dos dois IDs a conta tem, e gasta o mesmo tempo de uma verificação real (`perform_dummy_password_check`) pra não vazar, pelo timing, se a conta existe e é OAuth-only.

## Dados registrados

`google_id` (único, indexado) e `avatar_url` ficam gravados no usuário; nenhum token do Google é persistido -- o `access_token` obtido na troca do `code` é usado só na hora (buscar perfil) e descartado, nunca salvo no banco.
