# ruff: noqa: E501 -- módulo de textos de documentação; quebrar as frases piora a leitura.
"""Documentação OpenAPI da API, com os textos num lugar só para revisar o conjunto.

`build_openapi` acrescenta ao schema do FastAPI o fluxo de autenticação (cookie de
sessão e CSRF), a descrição de cada operação, os esquemas de segurança de cada rota,
tirados das dependências dela, e o formato de erro padrão. `scripts/export_openapi.py`
grava o resultado em docs/api/openapi.json, porque /docs não é servido em produção.
"""

from collections.abc import Callable, Iterator
from typing import Any

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from app.api.dependencies import get_current_session, require_authenticated_csrf, require_public_csrf
from app.api.openapi_examples import apply_examples
from app.api.v1.endpoints import (
    agent_skills,
    audit,
    auth,
    auth_oauth,
    clans,
    dashboard,
    health,
    llm,
    orchestrations,
    requests,
)
from app.core.config import settings

API_DESCRIPTION = """
API do **Multi-Agent Ecosystem**: um Orquestrador recebe solicitações técnicas,
seleciona as Agent Skills de cada domínio, consolida as respostas e passa o
resultado pelo Conselheiro (Quality Gate) antes da entrega.

## Autenticação

A API usa **cookie de sessão `HttpOnly`** (`agenthub_session`) e **proteção CSRF
por double-submit**: toda requisição que altera dados (`POST`, `PUT`, `PATCH`,
`DELETE`) precisa enviar o cabeçalho `X-CSRF-Token` com o mesmo valor do cookie
`agenthub_csrf`.

Para testar por aqui:

1. `GET /api/v1/auth/csrf` — cria o cookie `agenthub_csrf`.
2. `POST /api/v1/auth/login` (ou `/register`) — cria a sessão. Em navegador novo,
   o login responde `202` e envia um código ao e-mail; confirme em
   `POST /api/v1/auth/login/verify`.
3. Nesta página, o cabeçalho `X-CSRF-Token` é preenchido automaticamente a partir
   do cookie — não é preciso clicar em *Authorize*.

## Erros

Todo erro segue o mesmo formato (`ErrorResponse`): `error` (código), `message`
(texto para o usuário), `request_id` (para cruzar com os logs) e, em erros de
validação (`422`), `details` com o campo e o problema.

## Acesso

Não há papéis de usuário: cada pessoa acessa as próprias solicitações,
orquestrações e trilha de auditoria. Agent Skills seguem a visibilidade
`OFFICIAL` / `PRIVATE` / `CLAN`.
"""

TAGS_METADATA: list[dict[str, str]] = [
    {"name": "Status", "description": "Verificação de disponibilidade da API."},
    {
        "name": "Autenticação",
        "description": (
            "Cadastro, login (senha, GitHub, Google), código de verificação por e-mail em "
            "navegador novo, recuperação de senha, sessões e dados da própria conta."
        ),
    },
    {"name": "Dashboard", "description": "Resumo da atividade do usuário para a tela inicial."},
    {
        "name": "Solicitações técnicas",
        "description": (
            "Criação e qualificação de solicitações, complemento de contexto, anexos e "
            "revisão humana do resultado sinalizado pelo Conselheiro."
        ),
    },
    {
        "name": "Orquestrações",
        "description": "Rastreabilidade de uma orquestração pelo Trace ID: eventos, resultados e perguntas.",
    },
    {
        "name": "Agent Skills",
        "description": (
            "Catálogo de Agent Skills (criar, importar `modelo.md`, editar, ativar/desativar) "
            "e execução da orquestração sobre uma solicitação."
        ),
    },
    {"name": "Integração com LLM", "description": "Status do provedor de modelo, planejamento e rastros de invocação."},
    {"name": "Comitês", "description": "Grupos de usuários com regras próprias e Agent Skills visíveis só aos membros."},
    {"name": "Auditoria", "description": "Trilha de eventos das solicitações do próprio usuário."},
]

# (resumo, descrição) por "MÉTODO /caminho" relativo a API_V1_PREFIX.
OPERATION_DOCS: dict[str, tuple[str, str]] = {
    "GET /health": ("Status da API", "Retorna se a API está no ar. Não exige autenticação."),
    # Autenticação
    "GET /auth/csrf": (
        "Preparar token CSRF",
        "Cria o cookie `agenthub_csrf`, cujo valor deve ir no cabeçalho `X-CSRF-Token` das requisições "
        "que alteram dados.",
    ),
    "POST /auth/register": (
        "Criar conta",
        "Cria a conta com e-mail e senha e já inicia a sessão. A senha precisa de 12+ caracteres com "
        "maiúscula, minúscula, número e caractere especial. Desligado com `ALLOW_REGISTRATION=false`. "
        "Depois da resposta, envia o e-mail de conta criada; uma falha no envio não desfaz o cadastro.",
    ),
    "POST /auth/login": (
        "Entrar com e-mail e senha",
        "Em navegador já confiável, cria a sessão (`200`). Em navegador novo, responde `202` com "
        "`verification_required` e envia um código de 6 dígitos ao e-mail cadastrado — confirme em "
        "`POST /auth/login/verify`. Bloqueia a conta temporariamente após tentativas erradas seguidas.",
    ),
    "GET /auth/login/challenge": (
        "Consultar login pendente",
        "Informa se há um login aguardando o código neste navegador e para qual e-mail (mascarado) ele foi "
        "enviado. Usado depois do retorno do GitHub/Google. `410` se não houver login pendente.",
    ),
    "POST /auth/login/verify": (
        "Confirmar código de login",
        "Valida o código enviado por e-mail, cria a sessão e marca o navegador como confiável por "
        "`TRUSTED_DEVICE_DAYS`. `400` com as tentativas restantes se o código estiver errado; `410` se o "
        "login expirou ou as tentativas acabaram.",
    ),
    "POST /auth/login/resend": (
        "Reenviar código de login",
        "Envia um novo código para o login pendente. Respeita o intervalo mínimo entre envios (`429`) e "
        "não zera as tentativas já usadas.",
    ),
    "POST /auth/password/forgot": (
        "Esqueci minha senha",
        "Envia um link de redefinição ao e-mail, se ele estiver cadastrado. A resposta é sempre a mesma, "
        "exista ou não a conta, para não revelar e-mails cadastrados. Em produção sem SMTP "
        "(`EMAIL_BACKEND=console`), devolve 503 em vez de prometer um e-mail que não sai.",
    ),
    "POST /auth/password/reset": (
        "Redefinir senha",
        "Troca a senha usando o token do link enviado por e-mail (uso único, válido por "
        "`PASSWORD_RESET_TTL_MINUTES`). Encerra todas as sessões e revoga os navegadores confiáveis.",
    ),
    "POST /auth/renew": ("Renovar sessão", "Troca o token da sessão atual por um novo, estendendo a validade."),
    "POST /auth/logout": ("Sair", "Encerra a sessão atual e remove os cookies."),
    "POST /auth/logout-all": (
        "Sair de todas as sessões",
        "Encerra todas as sessões da conta e revoga os navegadores confiáveis (o próximo login pede código).",
    ),
    "GET /auth/me": ("Minha conta", "Dados do usuário autenticado."),
    "PATCH /auth/me": ("Alterar meu nome", "Atualiza o nome exibido do usuário autenticado."),
    "DELETE /auth/me": ("Excluir minha conta", "Exclui a conta do usuário autenticado e encerra a sessão."),
    "POST /auth/onboarding/complete": ("Concluir tour inicial", "Marca o tour de boas-vindas como concluído."),
    "POST /auth/me/password": (
        "Trocar minha senha",
        "Troca a senha informando a atual. Revoga os navegadores confiáveis. `409` em contas só com "
        "GitHub/Google.",
    ),
    "GET /auth/sessions": ("Minhas sessões", "Lista as sessões ativas da conta, indicando a atual."),
    "DELETE /auth/sessions/{session_id}": ("Encerrar uma sessão", "Revoga uma sessão específica da própria conta."),
    "GET /auth/github/login": (
        "Entrar com GitHub",
        "Redireciona o navegador para a autorização do GitHub. Abra pela barra de endereço, não por fetch.",
    ),
    "GET /auth/github/callback": (
        "Retorno do GitHub",
        "Chamado pelo GitHub após a autorização. Cria a sessão e redireciona ao dashboard ou, em navegador "
        "novo, envia o código por e-mail e redireciona para `/login?verify=1`.",
    ),
    "GET /auth/google/login": (
        "Entrar com Google",
        "Redireciona o navegador para a autorização do Google. Abra pela barra de endereço, não por fetch.",
    ),
    "GET /auth/google/callback": (
        "Retorno do Google",
        "Chamado pelo Google após a autorização. Mesmo comportamento do retorno do GitHub.",
    ),
    # Dashboard
    "GET /dashboard/summary": (
        "Resumo do dashboard",
        "Indicadores do usuário (execuções, taxa de sucesso, solicitações recentes, eventos) e totais do "
        "ecossistema.",
    ),
    # Solicitações
    "GET /requests": ("Minhas solicitações", "Lista as solicitações técnicas do usuário autenticado."),
    "POST /requests": (
        "Criar solicitação",
        "Registra uma solicitação técnica. O Orientador de Interação verifica se o contexto é suficiente: "
        "a solicitação fica `QUALIFIED` ou `AWAITING_CONTEXT`.",
    ),
    "GET /requests/{request_id}": ("Detalhe da solicitação", "Retorna uma solicitação do próprio usuário."),
    "POST /requests/{request_id}/review": (
        "Revisão humana",
        "Aprova ou rejeita o resultado de uma solicitação em `VALIDATING` (sinalizada pelo Conselheiro). "
        "Só quem abriu a solicitação revisa. Rejeitar exige justificativa em `notes`.",
    ),
    "POST /requests/{request_id}/context": (
        "Complementar contexto",
        "Acrescenta contexto a uma solicitação em `AWAITING_CONTEXT` e a reavalia.",
    ),
    "POST /requests/{request_id}/attachments": (
        "Anexar arquivo",
        "Envia um arquivo de apoio (multipart). Tipos e tamanho máximo são validados no servidor.",
    ),
    "GET /requests/{request_id}/attachments": ("Listar anexos", "Lista os anexos da solicitação."),
    "DELETE /requests/{request_id}/attachments/{attachment_id}": ("Remover anexo", "Remove um anexo da solicitação."),
    # Orquestrações
    "GET /orchestrations/{trace_id}": (
        "Detalhe da orquestração",
        "Solicitação, execução e eventos de uma orquestração, pelo Trace ID.",
    ),
    "GET /orchestrations/{trace_id}/events": ("Linha do tempo", "Eventos da orquestração em ordem."),
    "GET /orchestrations/{trace_id}/skill-results": (
        "Resultados das Agent Skills",
        "Resposta estruturada de cada Agent Skill executada na orquestração.",
    ),
    "GET /orchestrations/{trace_id}/follow-ups": (
        "Perguntas de acompanhamento",
        "Perguntas feitas depois da execução e as respostas das Agent Skills.",
    ),
    # LLM
    "GET /llm/status": (
        "Status do LLM",
        "Provedor, modelo padrão, modelos permitidos e uso de tokens do dia pelo usuário.",
    ),
    "GET /llm/invocations/{trace_id}": (
        "Invocações do LLM",
        "Rastro das chamadas ao modelo de uma orquestração (status, tokens, latência). O conteúdo integral "
        "não é armazenado por padrão.",
    ),
    "POST /llm/requests/{request_id}/plan": (
        "Gerar plano técnico",
        "Pede ao modelo um plano técnico estruturado para uma solicitação `QUALIFIED`. Respeita a cota "
        "diária de tokens (`429`).",
    ),
    # Agent Skills
    "GET /agent-skills": (
        "Catálogo de Agent Skills",
        "Skills visíveis ao usuário: oficiais, as próprias e as dos comitês de que participa. "
        "`only_active=false` inclui as desativadas.",
    ),
    "POST /agent-skills": (
        "Criar Agent Skill",
        "Cria uma skill pelo formulário assistido. O manifesto passa pela validação de governança "
        "(`422` lista todos os problemas). `visibility=CLAN` exige `clan_id` e permissão no comitê.",
    ),
    "POST /agent-skills/suggestions": (
        "Sugerir Agent Skills",
        "Compara a solicitação com as skills ativas por similaridade de embeddings e sugere as que não "
        "estão no comitê. Não chama o modelo de chat, e `available=false` indica provedor indisponível.",
    ),
    "GET /agent-skills/tools": (
        "Skills como tools",
        "Descritores das skills ativas no formato de tool (nome, descrição, schema de entrada).",
    ),
    "GET /agent-skills/ranking": ("Skills mais usadas", "Ranking das skills oficiais por número de execuções."),
    "POST /agent-skills/import": (
        "Importar `modelo.md`",
        "Registra uma skill a partir do conteúdo de um arquivo `modelo.md`.",
    ),
    "PUT /agent-skills/{skill_id}": (
        "Editar Agent Skill",
        "Substitui o manifesto da skill (mesmo id), revalidando-o. Permitido a quem criou a skill ou, numa "
        "skill de comitê, ao dono do comitê.",
    ),
    "GET /agent-skills/{skill_id}": ("Detalhe da Agent Skill", "Retorna uma skill visível ao usuário."),
    "PATCH /agent-skills/{skill_id}/enable": (
        "Reativar Agent Skill",
        "Volta a disponibilizar a skill para o Orquestrador. Mesma permissão da edição.",
    ),
    "PATCH /agent-skills/{skill_id}/disable": (
        "Desativar Agent Skill",
        "Tira a skill do catálogo ativo sem apagá-la. Mesma permissão da edição.",
    ),
    "POST /agent-skills/requests/{request_id}/execute": (
        "Executar orquestração",
        "Executa as Agent Skills sobre uma solicitação `QUALIFIED`, consolida as respostas e aplica o "
        "Quality Gate. Se o resultado não for aprovado, a solicitação vai para `VALIDATING` (revisão humana).",
    ),
    "POST /agent-skills/requests/{request_id}/cancel": (
        "Interromper orquestração",
        "Interrompe a execução em andamento. A linha do tempo registra a interrupção, e a solicitação passa a "
        "`CANCELLED`: dá para complementar o contexto e executar de novo. `409` se não estiver em execução.",
    ),
    "POST /agent-skills/requests/{request_id}/start": (
        "Iniciar orquestração em segundo plano",
        "Inicia a mesma execução de `/execute`, mas responde `202` sem esperar as Agent Skills. O andamento fica "
        "na linha do tempo de `GET /orchestrations/{trace_id}`. Aceita solicitações `QUALIFIED` ou `FAILED` (nova "
        "tentativa) e responde `409` se a execução já estiver em andamento.",
    ),
    "POST /agent-skills/requests/{request_id}/ask": (
        "Pergunta de acompanhamento",
        "Faz uma pergunta sobre uma solicitação já executada, opcionalmente direcionada a um domínio.",
    ),
    "POST /agent-skills/requests/{request_id}/ask/start": (
        "Iniciar pergunta em segundo plano",
        "Registra a pergunta e responde `202` sem esperar as Agent Skills. A resposta aparece em "
        "`GET /orchestrations/{trace_id}/follow-ups`. Responde `409` se outra pergunta ainda estiver em andamento.",
    ),
    # Auditoria
    "GET /audit/events": (
        "Trilha de auditoria",
        "Eventos das solicitações do próprio usuário, com filtros por período, ator e busca, e contagens "
        "do dia.",
    ),
    "GET /orchestrations/{trace_id}/artifacts": (
        "Listar arquivos gerados",
        "Arquivos entregues pelas Agent Skills, sem o conteúdo. Não chama o modelo.",
    ),
    "GET /orchestrations/{trace_id}/artifacts.zip": (
        "Baixar todos os arquivos",
        "ZIP com uma pasta por área, montado na hora. Não chama o modelo.",
    ),
    "GET /orchestrations/{trace_id}/artifacts/{artifact_id}": (
        "Ver arquivo gerado",
        "Conteúdo em texto, para pré-visualização. Não chama o modelo.",
    ),
    "GET /orchestrations/{trace_id}/artifacts/{artifact_id}/download": (
        "Baixar arquivo gerado",
        "Entrega o arquivo como download, sem abrir no navegador. Não chama o modelo.",
    ),
    # Comitês
    "GET /clans": ("Listar comitês", "Todos os comitês, ou só os do usuário com `mine=true`."),
    "POST /clans": (
        "Criar comitê",
        "Cria um comitê com as regras de acesso (`is_open`) e de quem adiciona Agent Skills e membros. "
        "Quem cria vira dono e membro.",
    ),
    "GET /clans/{clan_id}": ("Detalhe do comitê", "Dados, regras e membros do comitê."),
    "GET /clans/{clan_id}/skills": (
        "Listar skills do comitê",
        "Agent Skills disponíveis no comitê. Num comitê fechado, só para os membros.",
    ),
    "POST /clans/{clan_id}/skills": (
        "Adicionar skill ao comitê",
        "Adiciona uma Agent Skill publicada ou do próprio usuário, seguindo o `skills_policy` do comitê. "
        "`404` se a skill não existir ou não estiver visível, `409` se já estiver no comitê.",
    ),
    "DELETE /clans/{clan_id}/skills/{skill_id}": (
        "Remover skill do comitê",
        "Tira a Agent Skill do comitê, sem apagá-la do catálogo. Segue o `skills_policy` do comitê.",
    ),
    "PATCH /clans/{clan_id}/settings": (
        "Alterar comitê",
        "Renomeia o comitê e altera as regras. Só o dono. `409` se o nome já existir.",
    ),
    "POST /clans/{clan_id}/join": ("Entrar no comitê", "Entra num comitê aberto. `403` se o comitê for fechado."),
    "POST /clans/{clan_id}/members": (
        "Adicionar membro",
        "Adiciona um usuário pelo e-mail, conforme a regra `members_policy` do comitê.",
    ),
    "DELETE /clans/{clan_id}/members/{user_id}": (
        "Remover membro",
        "Remove um membro conforme `members_policy`. Sair do comitê (o próprio id) é sempre permitido; o dono "
        "não pode ser removido por outro membro.",
    ),
}

ERROR_RESPONSE_SCHEMA: dict[str, Any] = {
    "title": "ErrorResponse",
    "type": "object",
    "required": ["error", "message"],
    "properties": {
        "error": {"type": "string", "example": "HTTP_ERROR", "description": "Código do erro."},
        "message": {"type": "string", "example": "Solicitação não encontrada.", "description": "Texto para o usuário."},
        "request_id": {"type": "string", "nullable": True, "description": "Identificador para cruzar com os logs."},
        "details": {
            "type": "array",
            "description": "Só em erros de validação (422).",
            "items": {
                "type": "object",
                "properties": {"field": {"type": "string"}, "message": {"type": "string"}},
            },
        },
    },
}

_ERROR_DESCRIPTIONS = {
    "400": "Requisição inválida",
    "401": "Sessão ausente ou expirada",
    "403": "Sem permissão ou CSRF inválido",
    "404": "Não encontrado",
    "409": "Conflito com o estado atual",
    "410": "Não está mais disponível",
    "422": "Dados inválidos",
    "429": "Muitas requisições",
    "503": "Serviço externo indisponível",
}

_ENDPOINT_MODULES = (health, auth, auth_oauth, dashboard, requests, orchestrations, llm, agent_skills, audit, clans)


def _dependency_calls(dependant: Dependant) -> Iterator[Callable[..., Any]]:
    for sub in dependant.dependencies:
        if sub.call is not None:
            yield sub.call
        yield from _dependency_calls(sub)


def _route_info() -> dict[tuple[str, str], tuple[list[dict[str, list[str]]], bool]]:
    """(requisitos de segurança, tem rate limit) de cada operação, a partir das
    dependências reais da rota -- evita a documentação divergir do código."""
    result: dict[tuple[str, str], tuple[list[dict[str, list[str]]], bool]] = {}
    for module in _ENDPOINT_MODULES:
        for route in module.router.routes:
            if not isinstance(route, APIRoute):
                continue
            calls = set(_dependency_calls(route.dependant))
            requirement: dict[str, list[str]] = {}
            if get_current_session in calls:
                requirement["sessionCookie"] = []
            if require_authenticated_csrf in calls or require_public_csrf in calls:
                requirement["csrfHeader"] = []
            # Dependências criadas por app.core.rate_limit.rate_limit().
            rate_limited = any(call.__qualname__.startswith("rate_limit.") for call in calls)
            for method in route.methods or set():
                result[(method.lower(), f"{settings.api_v1_prefix}{route.path}")] = (
                    [requirement] if requirement else [],
                    rate_limited,
                )
    return result


def build_openapi(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=API_DESCRIPTION,
        routes=app.routes,
        tags=TAGS_METADATA,
    )
    components = schema.setdefault("components", {})
    components.setdefault("schemas", {})["ErrorResponse"] = ERROR_RESPONSE_SCHEMA
    components["securitySchemes"] = {
        "sessionCookie": {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.session_cookie_name,
            "description": "Cookie `HttpOnly` criado no login; o navegador o envia sozinho.",
        },
        "csrfHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-CSRF-Token",
            "description": f"Mesmo valor do cookie `{settings.csrf_cookie_name}` (preenchido automaticamente em /docs).",
        },
    }

    route_info = _route_info()
    error_ref = {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}}
    for path, operations in schema.get("paths", {}).items():
        relative = path.removeprefix(settings.api_v1_prefix)
        for method, operation in operations.items():
            docs = OPERATION_DOCS.get(f"{method.upper()} {relative}")
            if docs:
                operation["summary"], operation["description"] = docs
            requirement, rate_limited = route_info.get((method, path), ([], False))
            operation["security"] = requirement
            responses = operation.setdefault("responses", {})
            needed: set[str] = set()
            if operation.get("parameters") or operation.get("requestBody"):
                needed.add("422")
            if rate_limited:
                needed.add("429")
            if requirement and "sessionCookie" in requirement[0]:
                needed |= {"401", "403"}
            elif requirement:
                needed.add("403")
            if "{" in path:
                needed.add("404")
            for code in sorted(needed):
                responses.setdefault(code, {"description": _ERROR_DESCRIPTIONS[code], **error_ref})
            # O 422 padrão do FastAPI usa HTTPValidationError, mas o handler da
            # aplicação devolve ErrorResponse com `details`.
            if "422" in responses:
                responses["422"] = {"description": _ERROR_DESCRIPTIONS["422"], **error_ref}

    apply_examples(schema, api_prefix=settings.api_v1_prefix)
    app.openapi_schema = schema
    return schema


# Preenche o X-CSRF-Token a partir do cookie em toda chamada feita pelo Swagger UI.
SWAGGER_CSRF_INTERCEPTOR = """requestInterceptor: (request) => {
    const match = document.cookie.match(/(?:^|; )CSRF_COOKIE=([^;]*)/);
    if (match) request.headers['X-CSRF-Token'] = decodeURIComponent(match[1]);
    request.credentials = 'include';
    return request;
  },
  """.replace("CSRF_COOKIE", settings.csrf_cookie_name)
