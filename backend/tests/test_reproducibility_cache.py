# ruff: noqa: F811 -- o fixture provider vem de outro arquivo de testes.
import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.llm.providers.openrouter_provider import OpenRouterLLMProvider
from app.models import EmbeddingCacheEntry, LLMInvocation
from app.rag.cache import CachedEmbeddingProvider
from app.rag.factory import create_embedding_provider
from tests.conftest import authenticated_csrf_headers, create_qualified_request, register
from tests.test_clan_orchestration import OWNER, _clan
from tests.test_llm_providers import _build_request, _build_settings, _FakeOpenAIClient
from tests.test_protections import _plan, provider  # noqa: F401
from tests.test_skill_suggestions import WordCountEmbeddings

ROOT = Path(__file__).resolve().parent.parent.parent


def _sent_to_provider(monkeypatch, **settings_overrides) -> dict:
    calls: list[dict] = []
    monkeypatch.setattr("openai.OpenAI", lambda **kwargs: _FakeOpenAIClient(calls))
    OpenRouterLLMProvider(_build_settings(**settings_overrides)).generate_plan(
        _build_request(), llm_call_id="call-1", model="fake/modelo"
    )
    return calls[0]


class TestModelParameters:
    def test_temperature_and_seed_are_sent(self, monkeypatch) -> None:
        call = _sent_to_provider(monkeypatch, llm_temperature=0.0, llm_seed=42)

        assert call["temperature"] == 0.0
        assert call["seed"] == 42

    def test_defaults_ask_for_the_most_repeatable_answer(self) -> None:
        assert settings.llm_temperature == 0.0
        assert settings.llm_seed == 42

    def test_empty_values_are_not_sent(self, monkeypatch) -> None:
        call = _sent_to_provider(monkeypatch, llm_temperature=None, llm_seed=None)

        assert "temperature" not in call
        assert "seed" not in call

    def test_each_call_records_the_parameters_it_used(
        self, client: TestClient, provider, monkeypatch
    ) -> None:  # noqa: F811
        monkeypatch.setattr(settings, "llm_temperature", 0.0)
        monkeypatch.setattr(settings, "llm_seed", 7)
        register(client, OWNER)
        create_qualified_request(client)

        _plan()

        with SessionLocal() as db:
            invocation = db.scalar(select(LLMInvocation))
        assert invocation.temperature == 0.0
        assert invocation.seed == 7
        assert invocation.model == "fake/modelo"

    def test_changing_the_parameters_later_does_not_rewrite_history(
        self,
        client: TestClient,
        provider,  # noqa: F811
        monkeypatch,
    ) -> None:
        monkeypatch.setattr(settings, "llm_seed", 7)
        register(client, OWNER)
        create_qualified_request(client)
        _plan()

        monkeypatch.setattr(settings, "llm_seed", 8)
        _plan()

        with SessionLocal() as db:
            seeds = list(db.scalars(select(LLMInvocation.seed).order_by(LLMInvocation.created_at)))
        assert sorted(seeds) == [7, 8]


class TestEmbeddingModelConfig:
    def test_embedding_model_comes_from_the_configuration(self, monkeypatch) -> None:
        monkeypatch.setattr("openai.OpenAI", lambda **kwargs: object())

        embedding = create_embedding_provider(_build_settings(embedding_model="vendor/modelo:free"))

        assert embedding.model == "vendor/modelo:free"

    def test_default_keeps_the_model_of_the_indexed_base(self) -> None:
        assert settings.embedding_model == "openai/text-embedding-3-small"


class TestEmbeddingCache:
    def _count(self) -> int:
        with SessionLocal() as db:
            return db.scalar(select(func.count(EmbeddingCacheEntry.id)))

    def test_repeated_text_does_not_call_the_provider_again(self, client: TestClient) -> None:
        inner = WordCountEmbeddings()
        with SessionLocal() as db:
            cached = CachedEmbeddingProvider(inner, db, model="m1")
            first = cached.embed(["limite de crédito"])
            second = cached.embed(["limite de crédito"])

        assert first == second
        assert len(inner.batches) == 1

    def test_survives_between_processes_because_it_is_in_the_database(self, client: TestClient) -> None:
        inner = WordCountEmbeddings()
        with SessionLocal() as db:
            CachedEmbeddingProvider(inner, db, model="m1").embed(["limite"])
            db.commit()
        with SessionLocal() as other_session:
            CachedEmbeddingProvider(inner, other_session, model="m1").embed(["limite"])

        assert len(inner.batches) == 1

    def test_only_missing_texts_go_to_the_provider_and_order_is_kept(self, client: TestClient) -> None:
        inner = WordCountEmbeddings()
        with SessionLocal() as db:
            cached = CachedEmbeddingProvider(inner, db, model="m1")
            cached.embed(["b"])
            result = cached.embed(["a", "b", "c"])

        assert inner.batches[-1] == ["a", "c"]
        assert result == [inner._vector("a"), inner._vector("b"), inner._vector("c")]

    def test_other_model_does_not_reuse_the_vector(self, client: TestClient) -> None:
        inner = WordCountEmbeddings()
        with SessionLocal() as db:
            CachedEmbeddingProvider(inner, db, model="m1").embed(["limite"])
            CachedEmbeddingProvider(inner, db, model="m2").embed(["limite"])

        assert len(inner.batches) == 2

    def test_text_is_not_stored(self, client: TestClient) -> None:
        with SessionLocal() as db:
            CachedEmbeddingProvider(WordCountEmbeddings(), db, model="m1").embed(["texto confidencial"])
            db.commit()
            entry = db.scalar(select(EmbeddingCacheEntry))

        assert "texto" not in entry.text_hash
        assert not hasattr(entry, "text")

    def test_two_sessions_writing_the_same_text_do_not_fail(self, client: TestClient) -> None:
        inner = WordCountEmbeddings()
        with SessionLocal() as first, SessionLocal() as second:
            CachedEmbeddingProvider(inner, first, model="m1").embed(["limite"])
            first.commit()
            # A segunda sessão faz a mesma consulta como se não tivesse visto a primeira.
            cached = CachedEmbeddingProvider(inner, second, model="m1")
            cached._lookup = lambda hashes: {}
            assert cached.embed(["limite"]) == [inner._vector("limite")]
            second.commit()

        assert self._count() == 1

    def test_repeated_suggestion_does_not_generate_the_question_vector_again(
        self, client: TestClient, monkeypatch
    ) -> None:
        inner = WordCountEmbeddings()
        monkeypatch.setattr(
            "app.services.skill_suggestion_service.create_embedding_provider", lambda config: inner
        )
        register(client, OWNER)
        clan = _clan(client)
        payload = {"clan_id": clan["id"], "problem": "Calcular impostos.", "objective": "Avaliar."}

        for _ in range(2):
            response = client.post(
                "/api/v1/agent-skills/suggestions", json=payload, headers=authenticated_csrf_headers(client)
            )
            assert response.status_code == 200

        assert len(inner.batches) == 1

    def test_retriever_uses_the_cache(self, client: TestClient, monkeypatch) -> None:
        from app.rag import factory

        inner = WordCountEmbeddings()
        monkeypatch.setattr(factory, "create_embedding_provider", lambda config: inner)
        with SessionLocal() as db:
            retriever = factory.create_retriever(db, settings)

        assert isinstance(retriever.embedding_provider, CachedEmbeddingProvider)


class TestStaticCache:
    def test_built_assets_are_cached_for_a_long_time_and_the_page_is_not(self) -> None:
        config = json.loads((ROOT / "frontend/public/staticwebapp.config.json").read_text(encoding="utf-8"))
        rules = {route["route"]: route["headers"]["Cache-Control"] for route in config["routes"]}

        assert "immutable" in rules["/assets/*"]
        assert "max-age=31536000" in rules["/assets/*"]
        assert "no-cache" in rules["/index.html"]

    def test_local_nginx_follows_the_same_rule(self) -> None:
        nginx = (ROOT / "frontend/nginx.conf").read_text(encoding="utf-8")

        assert "location /assets/" in nginx
        assert "immutable" in nginx


