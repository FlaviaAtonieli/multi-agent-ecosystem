import hashlib
import re

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.rag.base import EmbeddingProvider
from app.rag.factory import RAGConfigurationError
from app.services import skill_suggestion_service as service
from tests.conftest import authenticated_csrf_headers, register
from tests.test_clan_orchestration import OTHER, OWNER, _add, _clan, _switch_user

URL = "/api/v1/agent-skills/suggestions"
DIMENSIONS = 512


class WordCountEmbeddings(EmbeddingProvider):
    """Vetor pelas palavras do texto: determinístico e sem custo. Textos com as mesmas
    palavras ficam próximos, e a similaridade de cosseno usada é a de verdade."""

    name = "teste"

    def __init__(self) -> None:
        self.batches: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.batches.append(texts)
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * DIMENSIONS
        for word in re.findall(r"\w+", text.lower()):
            vector[int(hashlib.sha256(word.encode()).hexdigest(), 16) % DIMENSIONS] += 1.0
        return vector


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> WordCountEmbeddings:
    fake = WordCountEmbeddings()
    monkeypatch.setattr(service, "create_embedding_provider", lambda config: fake)
    monkeypatch.setattr(settings, "skill_suggestion_min_score", 0.3)
    return fake


def _headers(client: TestClient) -> dict[str, str]:
    return authenticated_csrf_headers(client)


def _skill(client: TestClient, name: str, domain: str, objective: str, visibility: str = "OFFICIAL") -> dict:
    response = client.post(
        "/api/v1/agent-skills",
        json={
            "name": name,
            "version": "1.0",
            "author_origin": "Teste",
            "domain": domain,
            "objective": objective,
            "persona_instructions": "Especialista.",
            "capabilities": ["Analisar"],
            "expected_inputs": ["Contexto"],
            "produced_outputs": ["Riscos"],
            "operating_limits": ["Não decide sozinho"],
            "input_contract_ref": "solicitacao_analise_schema.v1",
            "output_contract_ref": "resposta_especialista_schema.v1",
            "validation_criteria": ["Contrato válido"],
            "visibility": visibility,
        },
        headers=_headers(client),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _taxes(client: TestClient) -> dict:
    return _skill(
        client, "Skill de Impostos", "Contabilidade", "Calcular impostos e tributos da folha fiscal."
    )


def _garden(client: TestClient) -> dict:
    return _skill(client, "Skill de Jardim", "Jardinagem", "Cuidar de plantas flores e sementes.")


def _ask(client: TestClient, clan_id: str, problem: str = "Precisamos calcular impostos e tributos fiscais."):
    return client.post(
        URL,
        json={"clan_id": clan_id, "problem": problem, "objective": "Avaliar o impacto.", "context": None},
        headers=_headers(client),
    )


class TestSuggestions:
    def test_suggests_related_skill_outside_the_clan(self, client: TestClient, provider) -> None:
        register(client, OWNER)
        taxes = _taxes(client)
        _garden(client)
        clan = _clan(client)

        body = _ask(client, clan["id"]).json()

        assert [item["id"] for item in body["suggestions"]] == [taxes["id"]]
        assert 0 < body["suggestions"][0]["score"] <= 1
        assert body["suggestions"][0]["domain"] == "Contabilidade"
        assert body["available"] is True
        assert body["catalog_gap"] is False

    def test_skill_already_in_the_clan_is_not_suggested(self, client: TestClient, provider) -> None:
        register(client, OWNER)
        taxes = _taxes(client)
        clan = _clan(client)
        _add(client, clan["id"], taxes["id"])

        body = _ask(client, clan["id"]).json()

        assert body["suggestions"] == []
        assert body["covered_by_clan"] is True
        assert body["catalog_gap"] is False
        assert body["best_clan_score"] > 0

    def test_tells_when_nothing_in_the_catalog_covers_the_subject(self, client: TestClient, provider) -> None:
        register(client, OWNER)
        _garden(client)
        clan = _clan(client)

        body = _ask(client, clan["id"], "Precisamos revisar contratos de exportação marítima.").json()

        assert body["suggestions"] == []
        assert body["catalog_gap"] is True
        assert body["covered_by_clan"] is False

    def test_best_match_comes_first_and_list_is_limited(
        self, client: TestClient, provider, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "skill_suggestion_max_results", 2)
        monkeypatch.setattr(settings, "skill_suggestion_min_score", 0.01)
        register(client, OWNER)
        best = _taxes(client)
        for index in range(3):
            _skill(
                client,
                f"Outra {index}",
                f"Area {index}",
                "Calcular impostos de outra coisa diferente qualquer.",
            )
        clan = _clan(client)

        suggestions = _ask(client, clan["id"]).json()["suggestions"]

        assert len(suggestions) == 2
        assert suggestions[0]["id"] == best["id"]
        assert suggestions[0]["score"] >= suggestions[1]["score"]

    def test_private_skill_of_someone_else_is_never_suggested(self, client: TestClient, provider) -> None:
        register(client, OWNER)
        _skill(
            client, "Impostos Privada", "Contabilidade", "Calcular impostos e tributos fiscais.", "PRIVATE"
        )
        _switch_user(client, OTHER)
        clan = _clan(client)

        assert _ask(client, clan["id"]).json()["suggestions"] == []

    def test_disabled_skill_is_not_suggested(self, client: TestClient, provider) -> None:
        register(client, OWNER)
        taxes = _taxes(client)
        client.patch(f"/api/v1/agent-skills/{taxes['id']}/disable", headers=_headers(client))
        clan = _clan(client)

        assert _ask(client, clan["id"]).json()["suggestions"] == []

    def test_says_if_the_person_can_add_to_the_clan(self, client: TestClient, provider) -> None:
        register(client, OWNER)
        _taxes(client)
        clan = _clan(client, is_open=True, skills_policy="OWNER_ONLY")
        assert _ask(client, clan["id"]).json()["can_add_to_clan"] is True

        _switch_user(client, OTHER)
        client.post(f"/api/v1/clans/{clan['id']}/join", headers=_headers(client))

        assert _ask(client, clan["id"]).json()["can_add_to_clan"] is False


class TestCost:
    def test_skill_vectors_are_reused_between_questions(self, client: TestClient, provider) -> None:
        register(client, OWNER)
        _taxes(client)
        clan = _clan(client)

        _ask(client, clan["id"])
        first_round = len(provider.batches)
        _ask(client, clan["id"], "Outra pergunta sobre outro assunto.")

        # A segunda pergunta só gera o vetor da própria pergunta.
        assert first_round == 2
        assert len(provider.batches) == 3
        assert len(provider.batches[-1]) == 1

    def test_editing_a_skill_generates_its_vector_again(self, client: TestClient, provider) -> None:
        register(client, OWNER)
        taxes = _taxes(client)
        clan = _clan(client)
        _ask(client, clan["id"])

        client.put(
            f"/api/v1/agent-skills/{taxes['id']}",
            json={
                "name": "Skill de Impostos",
                "version": "1.1",
                "author_origin": "Teste",
                "domain": "Contabilidade",
                "objective": "Novo objetivo sobre auditoria.",
                "persona_instructions": "Especialista.",
                "capabilities": ["Analisar"],
                "expected_inputs": ["Contexto"],
                "produced_outputs": ["Riscos"],
                "operating_limits": ["Não decide sozinho"],
                "input_contract_ref": "solicitacao_analise_schema.v1",
                "output_contract_ref": "resposta_especialista_schema.v1",
                "validation_criteria": ["Contrato válido"],
            },
            headers=_headers(client),
        )
        before = len(provider.batches)
        _ask(client, clan["id"])

        # A pergunta repetida vem do cache: só a skill editada gera vetor de novo.
        assert len(provider.batches) == before + 1
        assert "Novo objetivo sobre auditoria." in provider.batches[before][0]

    def test_does_not_call_the_chat_model(self, client: TestClient, provider, monkeypatch) -> None:
        def must_not_run(*args, **kwargs):
            raise AssertionError("A sugestão não pode chamar o modelo de chat.")

        monkeypatch.setattr("app.services.llm_service.generate_technical_plan", must_not_run)
        register(client, OWNER)
        _taxes(client)
        clan = _clan(client)

        assert _ask(client, clan["id"]).status_code == 200

    def test_personal_data_is_masked_before_leaving_the_system(self, client: TestClient, provider) -> None:
        register(client, OWNER)
        clan = _clan(client)

        _ask(client, clan["id"], "O erro aparece para ana.silva@empresa.com ao calcular impostos.")

        assert "ana.silva@empresa.com" not in provider.batches[-1][0]


class TestFailures:
    def test_without_provider_the_form_keeps_working(self, client: TestClient, monkeypatch) -> None:
        def no_provider(config):
            raise RAGConfigurationError("sem chave")

        monkeypatch.setattr(service, "create_embedding_provider", no_provider)
        register(client, OWNER)
        _taxes(client)
        clan = _clan(client)

        response = _ask(client, clan["id"])

        assert response.status_code == 200
        assert response.json()["available"] is False
        assert response.json()["catalog_gap"] is False

    def test_provider_failure_does_not_break(self, client: TestClient, provider, monkeypatch) -> None:
        def broken(texts):
            raise RuntimeError("fora do ar")

        monkeypatch.setattr(provider, "embed", broken)
        register(client, OWNER)
        _taxes(client)
        clan = _clan(client)

        response = _ask(client, clan["id"])

        assert response.status_code == 200
        assert response.json()["available"] is False


class TestAccess:
    def test_unknown_clan_is_not_found(self, client: TestClient, provider) -> None:
        register(client, OWNER)

        assert _ask(client, "nao-existe").status_code == 404

    def test_only_members_can_ask(self, client: TestClient, provider) -> None:
        register(client, OWNER)
        clan = _clan(client)
        _switch_user(client, OTHER)

        assert _ask(client, clan["id"]).status_code == 403

    def test_needs_login(self, client: TestClient, provider) -> None:
        assert client.post(
            URL, json={"clan_id": "x", "problem": "problema", "objective": "objetivo"}
        ).status_code in {
            401,
            403,
        }

    def test_problem_is_required(self, client: TestClient, provider) -> None:
        register(client, OWNER)
        clan = _clan(client)

        response = client.post(URL, json={"clan_id": clan["id"]}, headers=_headers(client))

        assert response.status_code == 422

    def test_vector_is_not_exposed_by_the_catalog(self, client: TestClient, provider) -> None:
        register(client, OWNER)
        _taxes(client)
        clan = _clan(client)
        _ask(client, clan["id"])

        assert "embedding" not in client.get("/api/v1/agent-skills").json()[0]
