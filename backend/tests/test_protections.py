"""Proteções que só eram exercitadas por testes que chamam a IA paga, ou por nenhum.

Foram encontradas quebrando o código de propósito: a proteção era desligada e a suíte
do CI continuava passando. Aqui elas rodam sempre, com um provedor falso no lugar do
modelo, e o resto do código de verdade.
"""

import os
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.agent_catalog.contracts import (
    AgenteEmissor,
    AnaliseEstruturada,
    Governanca,
    SkillToolResult,
)
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.rate_limit import limiter
from app.core.security import hash_token, utc_now
from app.llm.schemas import LLMPlan, LLMPlanRequest, LLMProviderResult, LLMUsage
from app.models import AuthSession, KnowledgeChunk, PasswordResetToken, TechnicalRequest, User
from app.quality_gate.service import evaluate
from app.rag.evaluation import precision_at_k, recall_at_k, reciprocal_rank
from app.rag.ingestion import chunk_text
from app.rag.retriever import InMemoryVectorRetriever
from app.services import llm_service
from app.services.llm_service import (
    LLMDisabledError,
    LLMModelNotAllowedError,
    LLMQuotaExceededError,
    generate_technical_plan,
)
from tests.conftest import (
    authenticated_csrf_headers,
    create_qualified_request,
    csrf_headers,
    register,
    user_id_for,
)
from tests.test_clan_orchestration import OTHER, OWNER, _add, _clan, _skill, _switch_user
from tests.test_skill_suggestions import WordCountEmbeddings

MODEL = "fake/modelo"


class FakeProvider:
    name = "fake"

    def __init__(self) -> None:
        self.requests: list[LLMPlanRequest] = []

    def generate_plan(self, request: LLMPlanRequest, *, llm_call_id: str, model: str) -> LLMProviderResult:
        self.requests.append(request)
        return LLMProviderResult(
            plan=LLMPlan(summary="Resumo."), usage=LLMUsage(input_tokens=60, output_tokens=60)
        )


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> FakeProvider:
    fake = FakeProvider()
    monkeypatch.setattr(llm_service, "create_llm_provider", lambda config: fake)
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "llm_provider", "openrouter")
    monkeypatch.setattr(settings, "llm_model", MODEL)
    monkeypatch.setattr(settings, "llm_allowed_models", MODEL)
    monkeypatch.setattr(settings, "rag_enabled", False)
    return fake


def _plan(requested_model: str | None = None, **request_fields) -> None:
    """Chama o serviço com a solicitação recém-criada, como uma skill faz."""
    with SessionLocal() as db:
        technical_request = db.scalar(select(TechnicalRequest).order_by(TechnicalRequest.created_at.desc()))
        for field, value in request_fields.items():
            setattr(technical_request, field, value)
        user = db.get(User, technical_request.owner_id)
        generate_technical_plan(
            db, technical_request=technical_request, user=user, requested_model=requested_model
        )
        db.commit()


class TestModelGate:
    def test_disabled_integration_does_not_call_the_provider(
        self, client: TestClient, provider, monkeypatch
    ) -> None:
        register(client, OWNER)
        create_qualified_request(client)
        monkeypatch.setattr(settings, "llm_enabled", False)

        with pytest.raises(LLMDisabledError):
            _plan()

        assert provider.requests == []

    def test_model_outside_the_allowed_list_does_not_call_the_provider(
        self, client: TestClient, provider
    ) -> None:
        register(client, OWNER)
        create_qualified_request(client)

        with pytest.raises(LLMModelNotAllowedError):
            _plan("outro/modelo-caro")

        assert provider.requests == []

    def test_daily_quota_stops_new_calls(self, client: TestClient, provider, monkeypatch) -> None:
        monkeypatch.setattr(settings, "llm_daily_token_limit_per_user", 100)
        register(client, OWNER)
        create_qualified_request(client)

        _plan()
        with pytest.raises(LLMQuotaExceededError):
            _plan()

        assert len(provider.requests) == 1

    def test_personal_data_is_masked_before_reaching_the_model(
        self, client: TestClient, provider, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "llm_redact_sensitive_data", True)
        register(client, OWNER)
        create_qualified_request(client)

        _plan(problem="O erro aparece para ana.silva@empresa.com com a chave sk-abcdefghijklmnopqrstuvwx.")

        sent = provider.requests[0].problem
        assert "ana.silva@empresa.com" not in sent
        assert "sk-abcdefghijklmnopqrstuvwx" not in sent


class TestAuthentication:
    def test_csrf_token_must_belong_to_the_session(self, client: TestClient) -> None:
        register(client, OWNER)
        # Cookie e cabeçalho iguais, para passar pela primeira checagem: sobra só a
        # que compara o token com o que foi emitido para esta sessão.
        forged = "token-forjado-pelo-atacante"
        client.cookies.delete("agenthub_csrf")
        client.cookies.set("agenthub_csrf", forged)

        response = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": forged})

        assert response.status_code == 403
        assert response.json()["message"] == "O token CSRF não pertence à sessão atual."

    def test_account_is_locked_after_too_many_wrong_passwords(self, client: TestClient, monkeypatch) -> None:
        monkeypatch.setattr(settings, "login_max_attempts", 3)
        register(client, OWNER)
        client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))

        for _ in range(3):
            wrong = client.post(
                "/api/v1/auth/login",
                json={"email": OWNER["email"], "password": "Senha-Errada#12345"},
                headers=csrf_headers(client),
            )
            assert wrong.status_code == 401

        right = client.post(
            "/api/v1/auth/login",
            json={"email": OWNER["email"], "password": OWNER["password"]},
            headers=csrf_headers(client),
        )
        assert right.status_code == 423

    def test_too_many_login_requests_are_limited(self, client: TestClient) -> None:
        limiter.clear()
        statuses = [
            client.post(
                "/api/v1/auth/login",
                json={"email": "ninguem@example.com", "password": "Senha-Errada#12345"},
                headers=csrf_headers(client),
            ).status_code
            for _ in range(6)
        ]

        assert statuses[:5] == [401] * 5
        assert statuses[5] == 429

    def test_expired_session_is_rejected(self, client: TestClient) -> None:
        register(client, OWNER)
        assert client.get("/api/v1/auth/me").status_code == 200
        with SessionLocal() as db:
            for auth_session in db.scalars(select(AuthSession)):
                auth_session.expires_at = utc_now() - timedelta(seconds=1)
            db.commit()

        assert client.get("/api/v1/auth/me").status_code == 401

    def test_expired_reset_link_is_rejected(self, client: TestClient) -> None:
        register(client, OWNER)
        raw_token = "token-de-redefinicao-de-teste"
        with SessionLocal() as db:
            db.add(
                PasswordResetToken(
                    user_id=user_id_for(OWNER["email"]),
                    token_hash=hash_token(raw_token),
                    expires_at=utc_now() - timedelta(seconds=1),
                )
            )
            db.commit()

        response = client.post(
            "/api/v1/auth/password/reset",
            json={"token": raw_token, "new_password": "Senha-Nova#123456"},
            headers=csrf_headers(client),
        )

        assert response.status_code == 400


class TestAuthorization:
    def test_other_person_cannot_review_a_request(self, client: TestClient) -> None:
        register(client, OWNER)
        technical_request = create_qualified_request(client)
        with SessionLocal() as db:
            db.get(TechnicalRequest, technical_request["id"]).status = "VALIDATING"
            db.commit()
        _switch_user(client, OTHER)

        response = client.post(
            f"/api/v1/requests/{technical_request['id']}/review",
            json={"decision": "approve", "notes": None},
            headers=authenticated_csrf_headers(client),
        )

        assert response.status_code == 404

    def test_clan_owner_who_left_cannot_add_skills(self, client: TestClient) -> None:
        register(client, OWNER)
        skill = _skill(client, "codigo_legado")
        clan = _clan(client)
        left = client.delete(
            f"/api/v1/clans/{clan['id']}/members/{user_id_for(OWNER['email'])}",
            headers=authenticated_csrf_headers(client),
        )
        assert left.status_code == 200, left.text

        assert _add(client, clan["id"], skill["id"]).status_code == 403

    def test_invalid_skill_is_not_registered(self, client: TestClient) -> None:
        register(client, OWNER)

        response = client.post(
            "/api/v1/agent-skills",
            json={
                "name": "Skill sem capacidades",
                "version": "1.0",
                "author_origin": "Teste",
                "domain": "Contabilidade",
                "objective": "Avaliar o impacto fiscal.",
                "persona_instructions": "Especialista.",
                "capabilities": [],
                "expected_inputs": ["Contexto"],
                "produced_outputs": ["Riscos"],
                "operating_limits": ["Não decide"],
                "input_contract_ref": "solicitacao_analise_schema.v1",
                "output_contract_ref": "resposta_especialista_schema.v1",
                "validation_criteria": [],
            },
            headers=authenticated_csrf_headers(client),
        )

        assert response.status_code == 422
        assert client.get("/api/v1/agent-skills").json() == []


def _result(confidence: str, *, summary: str = "Resumo da análise técnica.", domain: str = "codigo_legado"):
    return SkillToolResult(
        trace_id="TRC",
        agente_emissor=AgenteEmissor(nome=f"Skill {confidence}", dominio=domain),
        analise_estruturada=AnaliseEstruturada(resumo_executivo=summary),
        governanca=Governanca(nivel_confianca=confidence, justificativa_confianca="Motivo."),
    )


class TestQualityGate:
    def test_high_confidence_is_approved_without_review(self) -> None:
        verdict = evaluate([_result("ALTO")])

        assert verdict.approved is True
        assert verdict.requires_human_review is False

    def test_medium_confidence_is_approved_but_asks_for_review(self) -> None:
        verdict = evaluate([_result("MEDIO")])

        assert verdict.approved is True
        assert verdict.requires_human_review is True

    def test_low_confidence_is_rejected_and_says_who(self) -> None:
        verdict = evaluate([_result("ALTO"), _result("BAIXO")])

        assert verdict.approved is False
        assert verdict.requires_human_review is True
        assert "Skill BAIXO" in verdict.reasons[0]

    def test_no_answer_is_rejected(self) -> None:
        verdict = evaluate([])

        assert verdict.approved is False
        assert verdict.requires_human_review is True

    def test_divergent_answers_in_the_same_area_are_rejected(self) -> None:
        verdict = evaluate(
            [
                _result("ALTO", summary="Migrar banco relacional imediatamente hoje"),
                _result("ALTO", summary="Manter sistema atual sem alterar nada"),
            ]
        )

        assert verdict.approved is False
        assert "Divergência" in verdict.reasons[0]

    def test_different_answers_in_different_areas_are_expected(self) -> None:
        verdict = evaluate(
            [
                _result("ALTO", summary="Migrar banco relacional imediatamente hoje"),
                _result("ALTO", summary="Manter sistema atual sem alterar nada", domain="regras_negocio"),
            ]
        )

        assert verdict.approved is True


class TestRagPipeline:
    def test_retrieval_returns_the_most_similar_chunks_first(self, client: TestClient) -> None:
        vectors = WordCountEmbeddings()
        texts = [
            "limite de crédito do cliente",
            "plantas e flores do jardim",
            "limite de crédito por segmento",
        ]
        with SessionLocal() as db:
            for index, text in enumerate(texts):
                db.add(
                    KnowledgeChunk(
                        artifact_name=f"doc{index}.md",
                        source_type="teste",
                        content=text,
                        embedding=vectors.embed([text])[0],
                        chunk_index=0,
                        char_start=0,
                        char_end=len(text),
                    )
                )
            db.commit()

            retrieved = InMemoryVectorRetriever(db, vectors).retrieve("limite de crédito", top_k=2)

        assert [chunk.artifact_name for chunk in retrieved] == ["doc0.md", "doc2.md"]
        assert retrieved[0].score >= retrieved[1].score

    def test_chunks_overlap_so_information_is_not_cut_in_half(self) -> None:
        chunks = chunk_text("abcdefghij", max_chars=4, overlap=2)

        assert [chunk[0] for chunk in chunks] == ["abcd", "cdef", "efgh", "ghij"]

    def test_overlap_must_be_smaller_than_the_window(self) -> None:
        with pytest.raises(ValueError, match="overlap"):
            chunk_text("abc", max_chars=2, overlap=2)

    def test_metrics_follow_their_definition(self) -> None:
        retrieved = ["errado.md", "certo.md", "certo.md", "outro.md"]
        relevant = {"certo.md", "faltou.md"}

        # Repetições contam uma vez: os documentos distintos são errado, certo e outro.
        assert precision_at_k(retrieved, relevant, 3) == pytest.approx(1 / 3)
        assert recall_at_k(retrieved, relevant, 3) == pytest.approx(1 / 2)
        assert reciprocal_rank(retrieved, relevant) == pytest.approx(1 / 2)
        assert reciprocal_rank(["errado.md"], relevant) == 0.0


def test_suite_runs_on_the_requested_database() -> None:
    """Sem isso, um erro de configuração faria o job de PostgreSQL rodar em SQLite sem avisar."""
    if os.environ.get("TEST_DATABASE_URL"):
        assert engine.url.get_backend_name() == "postgresql"
    else:
        assert engine.url.get_backend_name() == "sqlite"
