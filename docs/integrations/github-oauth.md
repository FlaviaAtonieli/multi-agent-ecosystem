# Login com GitHub

## Papel na aplicação

Método de autenticação **adicional**, ao lado do fluxo de e-mail/senha já existente -- não o substitui. Uma conta pode ser criada por e-mail/senha (`password_hash` preenchido) ou por GitHub (`github_id` preenchido, `password_hash` nulo); hoje não existe fluxo pra vincular as duas depois de criadas separadamente.

Desabilitado por padrão (`GITHUB_OAUTH_ENABLED=false`): o projeto sobe normalmente sem nenhuma credencial de OAuth configurada -- só o botão "Continuar com GitHub" some do frontend e `/api/v1/auth/github/*` responde `404`.

## Criando o GitHub OAuth App

Cada ambiente (dev local, produção) deve ter seu próprio OAuth App -- não reaproveite credenciais entre eles.

1. Acesse **GitHub → foto de perfil (canto superior direito) → Settings → Developer settings → OAuth Apps → New OAuth App** (ou diretamente [github.com/settings/developers](https://github.com/settings/developers)).
2. Preencha:
   - **Application name**: qualquer nome identificável (ex.: `AgentHub (dev local)`).
   - **Homepage URL**: `http://localhost:5173` (Vite direto) ou `http://localhost:3000` (via `docker compose`).
   - **Authorization callback URL**: precisa bater **exatamente** com `GITHUB_OAUTH_REDIRECT_URI` do `.env` -- por padrão, `http://localhost:8000/api/v1/auth/github/callback`.
3. Clique em **Register application**.
4. Na página do app criado, copie o **Client ID**.
5. Clique em **Generate a new client secret** e copie o valor mostrado **na hora** -- o GitHub não mostra o secret de novo depois.
6. Preencha no `.env` (raiz do projeto, ou `backend/.env` se rodando o backend fora do Docker):

   ```env
   GITHUB_OAUTH_ENABLED=true
   GITHUB_CLIENT_ID=<Client ID copiado>
   GITHUB_CLIENT_SECRET=<Client secret copiado>
   GITHUB_OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/github/callback
   FRONTEND_BASE_URL=http://localhost:3000
   ```

7. Reinicie o backend. O botão "Continuar com GitHub" passa a aparecer nas telas de login e cadastro.

Pra produção, repita o processo com um OAuth App separado apontando pro domínio real (`https://seu-dominio.com/api/v1/auth/github/callback`), e preencha as mesmas variáveis em `.env.production.example`/no gerenciador de segredos do deploy.

## Fluxo (authorization code)

```text
Usuário clica "Continuar com GitHub"
  -> navegador GET /api/v1/auth/github/login
  -> backend gera `state` aleatório, grava num cookie curto (10 min) e redireciona pro GitHub
  -> usuário autoriza no GitHub
  -> GitHub redireciona o navegador pra /api/v1/auth/github/callback?code=...&state=...
  -> backend valida o `state` contra o cookie (proteção CSRF própria do OAuth --
     distinta do CSRF da sessão, que não se aplica aqui por ser navegação de página inteira)
  -> troca o `code` por um access_token (chamada servidor-a-servidor com o client_secret)
  -> busca o perfil e o e-mail verificado do usuário no GitHub
  -> encontra ou cria a conta, abre sessão normal (mesmos cookies de sempre)
  -> redireciona pro frontend (FRONTEND_BASE_URL/dashboard, ou /login?error=... em caso de falha)
```

## Resolução do e-mail (`fetch_github_profile`, `app/services/github_oauth_service.py`)

O campo `email` retornado por `GET /user` é o e-mail **público** do perfil do GitHub e não tem garantia de estar marcado como `verified` pela API. Por isso `fetch_github_profile` **nunca** usa esse campo diretamente -- sempre consulta `GET /user/emails` (requer o escopo `user:email`, já pedido) e escolhe o primário verificado (ou, na falta dele, qualquer verificado). Sem nenhum e-mail verificado acessível, a request falha com `github_oauth_failed` antes de tocar o banco. Usar um e-mail não verificado abriria a mesma classe de risco que a resolução de conta abaixo já evita por outro ângulo (alguém reivindicando acesso via um e-mail que não controla de fato).

## Resolução de conta (`find_or_create_user`, `app/services/github_oauth_service.py`)

1. **Por `github_id`** primeiro (estável mesmo que o usuário troque de e-mail ou nome no GitHub) -- se existe, entra nessa conta e atualiza nome/avatar.
2. Se não existe por `github_id`, verifica **por e-mail**. Se já existe uma conta (de e-mail/senha ou de outro `github_id`) com esse e-mail, a request é recusada com um erro claro (`github_email_in_use`) -- **não há auto-link silencioso por e-mail**. Motivo: esta aplicação não verifica e-mail no cadastro por senha, então auto-linkar por e-mail abriria uma via de account takeover (alguém registra o e-mail da vítima por senha antes dela logar com GitHub, e herdaria o acesso). Vincular as duas contas manualmente é um fluxo que ainda não existe -- possível evolução futura.
3. Só então cria uma conta nova, papel `USER`, sem senha (`password_hash=None`), respeitando `ALLOW_REGISTRATION`.

## Erros expostos ao frontend

O callback sempre redireciona (nunca deixa uma tela de erro JSON crua no navegador). `/login?error=<código>`:

| código | motivo |
|---|---|
| `github_oauth_failed` | `state` ausente/não bate (possível CSRF ou cookie expirado), ou qualquer falha na troca de código/consulta de perfil com o GitHub |
| `github_email_in_use` | o e-mail verificado do GitHub já pertence a outra conta |
| `account_inactive` | a conta (já existente) está desativada pelo admin |

## Login por senha numa conta GitHub-only

Uma conta criada via GitHub não tem `password_hash`. `POST /auth/login` com e-mail/senha pra essa conta retorna `401` com uma mensagem indicando pra usar o botão do GitHub -- `authenticate_user` (`app/services/auth_service.py`) trata isso antes de tentar comparar contra um hash inexistente, gastando o mesmo tempo de uma verificação real (`perform_dummy_password_check`) pra não vazar, pelo timing, se a conta existe e é GitHub-only.

## Dados registrados

`github_id` (único, indexado) e `avatar_url` ficam gravados no usuário; nenhum token do GitHub é persistido -- o `access_token` obtido na troca do `code` é usado só na hora (buscar perfil/e-mail) e descartado, nunca salvo no banco.
