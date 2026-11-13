# ruff: noqa: E501 -- módulo de textos de documentação; quebrar as frases piora a leitura.
"""Descrições de campos e exemplos do Swagger.

Separado de openapi_docs.py porque são dados de exemplo. tests/test_api_examples.py
valida cada exemplo com os mesmos schemas da API, então um exemplo desatualizado faz
o teste falhar. Todos os dados aqui são fictícios.
"""

from typing import Any

_MODEL = "Modelo da lista permitida (`LLM_ALLOWED_MODELS`). Sem valor, usa o modelo padrão."
_VISIBILITY = "`OFFICIAL` publica no catálogo, `PRIVATE` deixa só para você e `CLAN` registra a skill em um comitê."
_CLAN_ID = "Obrigatório quando `visibility` é `CLAN`."
_NEW_SECRET_RULE = "Nova senha: pelo menos 12 caracteres, com maiúscula, minúscula, número e caractere especial."
_SKILLS_POLICY = "Quem adiciona e remove Agent Skills do comitê: `ALL_MEMBERS` ou `OWNER_ONLY`."
_MEMBERS_POLICY = "Quem adiciona e remove membros: `ALL_MEMBERS` ou `OWNER_ONLY`."
_IS_OPEN = "Se verdadeiro, qualquer pessoa pode entrar no comitê sozinha."

# Campos que a API recebe. Um campo novo sem descrição faz o teste falhar.
FIELD_DOCS: dict[str, dict[str, str]] = {
    "AgentSkillExecutionRequest": {"model": _MODEL},
    "AgentSkillManifestCreate": {
        "visibility": _VISIBILITY,
        "clan_id": _CLAN_ID,
        "name": "Nome da skill no catálogo.",
        "version": "Versão da skill, como `1.0`.",
        "author_origin": "Quem criou a skill, ou de onde ela veio.",
        "domain": "Área de atuação, em texto livre. As áreas do catálogo oficial mantêm um único valor.",
        "objective": "O que a skill analisa. Também é usado pelo motor de sugestão.",
        "capabilities": "O que a skill sabe fazer. Pelo menos uma.",
        "expected_inputs": "O que a skill precisa receber.",
        "produced_outputs": "O que a skill entrega.",
        "operating_limits": "O que a skill não deve fazer.",
        "input_contract_ref": "Contrato de entrada que a skill segue.",
        "output_contract_ref": "Contrato de saída que a skill segue.",
        "security_rules": "Regras de segurança que a skill respeita.",
        "usage_examples": "Exemplos de uso.",
        "validation_criteria": "Como conferir a resposta da skill.",
        "uses_external_services": "Se a skill depende de serviços externos.",
        "persona_instructions": "Instruções de papel e foco enviadas ao modelo em cada chamada.",
    },
    "AgentSkillManifestImport": {
        "manifest_markdown": "Conteúdo do arquivo `modelo.md`.",
        "visibility": _VISIBILITY,
        "clan_id": _CLAN_ID,
    },
    "Body_upload_request_attachment_api_v1_requests__request_id__attachments_post": {
        "file": "Arquivo de texto puro, como código, Markdown ou JSON. PDF e DOCX não são aceitos.",
    },
    "ClanCreate": {
        "name": "Nome do comitê. Precisa ser único.",
        "is_open": _IS_OPEN,
        "skills_policy": _SKILLS_POLICY,
        "members_policy": _MEMBERS_POLICY,
    },
    "ClanMemberAdd": {"email": "E-mail de uma pessoa já cadastrada."},
    "ClanSettingsUpdate": {
        "name": "Novo nome. Sem valor, mantém o atual.",
        "is_open": _IS_OPEN,
        "skills_policy": _SKILLS_POLICY,
        "members_policy": _MEMBERS_POLICY,
    },
    "ClanSkillAdd": {"agent_skill_id": "Skill publicada, ou sua, para adicionar ao comitê."},
    "FollowUpQuestionCreate": {
        "question": "Pergunta sobre a análise já feita.",
        "target_domain": "Área que deve responder. Sem valor, todas as áreas envolvidas respondem.",
        "model": _MODEL,
    },
    "LoginCodeVerify": {"code": "Código de 6 dígitos enviado por e-mail."},
    "LoginRequest": {"email": "E-mail da conta.", "password": "Senha da conta."},  # NOSONAR: texto ou exemplo de documentação, não é credencial
    "PasswordChange": {"current_password": "Senha atual.", "new_password": _NEW_SECRET_RULE},  # NOSONAR: texto ou exemplo de documentação, não é credencial
    "PasswordForgot": {"email": "E-mail da conta."},
    "PasswordReset": {"token": "Token recebido no link por e-mail.", "new_password": _NEW_SECRET_RULE},
    "SkillSuggestionRequest": {
        "clan_id": "Comitê que vai responder. Só skills fora dele são sugeridas.",
        "title": "Título da solicitação.",
        "problem": "Problema a analisar.",
        "objective": "Resultado esperado.",
        "context": "Contexto técnico, como módulos e tecnologias.",
    },
    "TechnicalRequestContextUpdate": {"context": "Contexto que faltava para qualificar a solicitação."},
    "TechnicalRequestCreate": {
        "title": "Identificação curta e específica.",
        "problem": "Comportamento atual, divergência ou dúvida técnica.",
        "objective": "Resposta ou resultado esperado.",
        "context": "Módulos, tecnologias e dependências. Contexto insuficiente deixa a solicitação em `AWAITING_CONTEXT`.",
        "restrictions": "O que a análise deve respeitar.",
        "clan_id": "Comitê cujas Agent Skills vão responder. É preciso ser membro.",
        "requested_domains": "Áreas escolhidas dentro do comitê. Vazio significa todas as skills ativas do comitê.",
    },
    "TechnicalRequestReview": {
        "decision": "`approve` aprova e `reject` rejeita a resposta.",
        "notes": "Justificativa. Obrigatória ao rejeitar.",
    },
    "UserCreate": {
        "name": "Nome completo.",
        "email": "E-mail da conta.",
        "password": "Senha: pelo menos 12 caracteres, com maiúscula, minúscula, número e caractere especial.",  # NOSONAR: texto ou exemplo de documentação, não é credencial
    },
    "UserNameUpdate": {"name": "Novo nome."},
}

_TIMESTAMP = "2026-11-04T12:00:00Z"
_REQUEST_ID = "7f3c1a2e-5b1d-4c8e-9a10-2f6d8e4b7c01"
_CLAN = "1d9e4b6a-3c2f-4a7b-8e05-6c1f2d3a9b10"

REQUEST_EXAMPLES: dict[str, dict[str, Any]] = {
    "POST /auth/register": {
        "name": "Pessoa de Exemplo",
        "email": "pessoa@example.com",
        "password": "Exemplo-De-Senha#2026",  # NOSONAR: texto ou exemplo de documentação, não é credencial
    },
    "POST /auth/login": {"email": "pessoa@example.com", "password": "Exemplo-De-Senha#2026"},  # NOSONAR: texto ou exemplo de documentação, não é credencial
    "POST /clans": {
        "name": "Time de Crédito",
        "is_open": False,
        "skills_policy": "ALL_MEMBERS",
        "members_policy": "OWNER_ONLY",
    },
    "POST /clans/{clan_id}/skills": {"agent_skill_id": "a4c2e8f1-7b3d-4e6a-9c10-5d2f8b1a3e77"},
    "POST /agent-skills": {
        "name": "Skill de Impostos",
        "version": "1.0",
        "author_origin": "Escritório de Contabilidade",
        "domain": "Contabilidade",
        "objective": "Avaliar o impacto fiscal de uma mudança em um sistema.",
        "persona_instructions": "Você é especialista em tributos. Aponte riscos fiscais e cite a evidência.",
        "capabilities": ["Avaliar impostos sobre operações"],
        "expected_inputs": ["Descrição da mudança"],
        "produced_outputs": ["Riscos fiscais"],
        "operating_limits": ["Não substitui o contador responsável"],
        "input_contract_ref": "solicitacao_analise_schema.v1",
        "output_contract_ref": "resposta_especialista_schema.v1",
        "validation_criteria": ["Resposta segue o contrato de saída"],
        "visibility": "OFFICIAL",
    },
    "POST /agent-skills/suggestions": {
        "clan_id": _CLAN,
        "title": "Limite de crédito por segmento",
        "problem": "O limite é fixo para todos os clientes e os impostos variam por segmento.",
        "objective": "Avaliar o impacto de limites diferentes por segmento.",
        "context": "Sistema legado em Java. O limite é usado na aprovação de pedidos.",
    },
    "POST /requests": {
        "title": "Limite de crédito por segmento",
        "problem": "O limite é fixo para todos os clientes, no CreditLimitService.",
        "objective": "Avaliar o impacto de limites diferentes por segmento.",
        "context": "Sistema legado em Java. O limite é usado na aprovação de pedidos e no RiskBatchJob.",
        "restrictions": ["Não interromper a aprovação de pedidos"],
        "clan_id": _CLAN,
        "requested_domains": ["codigo_legado", "regras_negocio"],
    },
    "POST /agent-skills/requests/{request_id}/start": {"model": "openai/gpt-5-mini"},
    "POST /agent-skills/requests/{request_id}/ask/start": {
        "question": "Qual é o maior risco desta mudança?",
        "target_domain": "regras_negocio",
        "model": "openai/gpt-5-mini",
    },
    "POST /requests/{request_id}/review": {
        "decision": "approve",
        "notes": "Análise conferida com o time de crédito.",
    },
}

# Operação: (código da resposta, exemplo).
RESPONSE_EXAMPLES: dict[str, tuple[str, Any]] = {
    "POST /agent-skills/suggestions": (
        "200",
        {
            "available": True,
            "suggestions": [
                {
                    "id": "a4c2e8f1-7b3d-4e6a-9c10-5d2f8b1a3e77",
                    "name": "Skill de Impostos",
                    "domain": "Contabilidade",
                    "objective": "Avaliar o impacto fiscal de uma mudança em um sistema.",
                    "score": 0.62,
                }
            ],
            "best_clan_score": 0.31,
            "covered_by_clan": False,
            "catalog_gap": False,
            "can_add_to_clan": True,
        },
    ),
    "POST /requests": (
        "201",
        {
            "id": _REQUEST_ID,
            "trace_id": "TRC-20261104-D8E740",
            "title": "Limite de crédito por segmento",
            "problem": "O limite é fixo para todos os clientes, no CreditLimitService.",
            "objective": "Avaliar o impacto de limites diferentes por segmento.",
            "context": "Sistema legado em Java. O limite é usado na aprovação de pedidos e no RiskBatchJob.",
            "restrictions": ["Não interromper a aprovação de pedidos"],
            "requested_domains": ["codigo_legado", "regras_negocio"],
            "clan_id": _CLAN,
            "status": "QUALIFIED",
            "created_at": _TIMESTAMP,
            "updated_at": _TIMESTAMP,
            "consolidated_response": None,
        },
    ),
    "GET /orchestrations/{trace_id}/artifacts": (
        "200",
        [
            {
                "id": "c7b1d3e9-2a4f-4d6c-8e11-9f0a1b2c3d44",
                "filename": "src/limite.py",
                "size_bytes": 2048,
                "agent_skill_name": "Agent Skill de Código Legado",
                "domain": "codigo_legado",
                "created_at": _TIMESTAMP,
            }
        ],
    ),
}

# Respostas que são arquivos, e não JSON.
FILE_RESPONSES: dict[str, str] = {
    "GET /orchestrations/{trace_id}/artifacts.zip": "application/zip",
    "GET /orchestrations/{trace_id}/artifacts/{artifact_id}/download": "application/octet-stream",
}

SERVERS: list[dict[str, str]] = [
    {"url": "http://localhost:8000", "description": "Desenvolvimento local"},
    {"url": "https://jolly-grass-0a3af3f10.2.azurestaticapps.net", "description": "Produção"},
]


def apply_examples(schema: dict[str, Any], *, api_prefix: str) -> None:
    schema["servers"] = SERVERS

    components = schema["components"]["schemas"]
    for name, fields in FIELD_DOCS.items():
        properties = components[name]["properties"]
        for field, description in fields.items():
            properties[field]["description"] = description

    def operation(key: str) -> dict[str, Any]:
        method, path = key.split(" ", 1)
        return schema["paths"][api_prefix + path][method.lower()]

    for key, example in REQUEST_EXAMPLES.items():
        operation(key)["requestBody"]["content"]["application/json"]["example"] = example
    for key, (code, example) in RESPONSE_EXAMPLES.items():
        operation(key)["responses"][code]["content"]["application/json"]["example"] = example
    for key, media_type in FILE_RESPONSES.items():
        operation(key)["responses"]["200"]["content"] = {
            media_type: {"schema": {"type": "string", "format": "binary"}}
        }
