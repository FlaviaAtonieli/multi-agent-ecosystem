"""Mede o motor de sugestão com embeddings reais, contra um gabarito manual.

Fica fora do CI, como os demais testes `llm`. Roda com uma OPENROUTER_API_KEY real:

    pytest tests/test_skill_suggestion_quality.py -m llm -s

Cada pergunta traz a área que deveria ser sugerida, com um clã vazio, de modo que
todo o catálogo oficial concorre. As perguntas evitam repetir o nome das áreas, para
a medição não premiar só a coincidência de palavras. O resultado orienta o valor de
SKILL_SUGGESTION_MIN_SCORE.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import limiter
from app.db.seed_agent_skills import seed_agent_skills
from app.rag.evaluation import precision_at_k, recall_at_k, reciprocal_rank
from tests.conftest import authenticated_csrf_headers, register
from tests.test_clan_orchestration import OWNER, _clan

TOP_K = 3

ON_TOPIC: list[tuple[str, str]] = [
    ("Ninguém entende mais o módulo COBOL de 20 anos que calcula o faturamento.", "codigo_legado"),
    ("Um sistema antigo em Java 6 sem documentação precisa ganhar uma função nova.", "codigo_legado"),
    ("O desconto progressivo muda conforme o segmento do cliente e o contrato.", "regras_negocio"),
    ("A política de aprovação de crédito mudou e precisamos saber o que isso afeta.", "regras_negocio"),
    ("Os módulos estão muito acoplados e queremos separar em serviços menores.", "arquitetura_software"),
    (
        "Precisamos decidir entre monólito modular e microsserviços para o novo produto.",
        "arquitetura_software",
    ),
    (
        "Encontramos um endpoint que aceita SQL injection e expõe dados de outros clientes.",
        "seguranca_informacao",
    ),
    (
        "Tokens de acesso estão aparecendo em texto puro e qualquer um consegue entrar.",
        "seguranca_informacao",
    ),
    ("A suíte falha de vez em quando sem motivo e quase não cobre os cenários críticos.", "qualidade_testes"),
    ("Toda entrega quebra algo que já funcionava, e faltam testes de regressão.", "qualidade_testes"),
    (
        "O job falha de madrugada e só descobrimos de manhã, porque não há alertas nem logs.",
        "observabilidade_monitoramento",
    ),
    (
        "Não temos métricas nem painéis para saber quando a API começa a degradar.",
        "observabilidade_monitoramento",
    ),
    (
        "A tela demora 30 segundos porque cada item dispara uma consulta ao banco (N+1).",
        "performance_escalabilidade",
    ),
    (
        "O sistema não aguenta o pico de acessos da Black Friday e a fila explode.",
        "performance_escalabilidade",
    ),
    ("Guardamos CPF por tempo indeterminado e não sabemos a base legal para isso.", "dados_privacidade"),
    ("Um titular pediu a exclusão de todos os dados pessoais, conforme a LGPD.", "dados_privacidade"),
    (
        "O deploy é manual por SSH e o ambiente de homologação é diferente da produção.",
        "infraestrutura_devops",
    ),
    ("Queremos descrever os servidores com Terraform e automatizar o pipeline.", "infraestrutura_devops"),
    ("Um parceiro mudou o contrato do webhook e nossa integração parou sem aviso.", "apis_integracoes"),
    (
        "Precisamos versionar a REST pública e colocar timeout e circuit breaker nas chamadas.",
        "apis_integracoes",
    ),
]

OFF_TOPIC = [
    "Qual a melhor receita de bolo de cenoura com cobertura de chocolate?",
    "Quero planejar uma viagem de férias para as praias do Nordeste.",
    "Como treinar um cachorro filhote para não latir à noite?",
]


@pytest.mark.llm
def test_suggestion_quality_against_ground_truth(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "bootstrap_admin_email", OWNER["email"])
    monkeypatch.setattr(settings, "skill_suggestion_min_score", 0.0)
    monkeypatch.setattr(settings, "skill_suggestion_max_results", TOP_K)
    register(client, OWNER)
    seed_agent_skills()
    clan_id = _clan(client)["id"]

    def ask(problem: str) -> list[dict]:
        # A medição faz mais consultas que o limite por minuto da API.
        limiter.clear()
        response = client.post(
            "/api/v1/agent-skills/suggestions",
            json={"clan_id": clan_id, "problem": problem, "objective": "Avaliar o que fazer."},
            headers=authenticated_csrf_headers(client),
        )
        assert response.status_code == 200, response.text
        assert response.json()["available"] is True
        return response.json()["suggestions"]

    precisions, recalls, ranks, top_scores = [], [], [], []
    for problem, expected in ON_TOPIC:
        suggestions = ask(problem)
        ranked = [item["domain"] for item in suggestions]
        precisions.append(precision_at_k(ranked, {expected}, TOP_K))
        recalls.append(recall_at_k(ranked, {expected}, TOP_K))
        ranks.append(reciprocal_rank(ranked, {expected}))
        top_scores.append(suggestions[0]["score"])
        print(f"{ranks[-1]:.2f} {suggestions[0]['score']:.3f} {expected:32} {ranked[0]:32} {problem[:50]}")

    off_topic_scores = [ask(problem)[0]["score"] for problem in OFF_TOPIC]
    total = len(ON_TOPIC)
    print(
        f"\nn={total} P@{TOP_K}={sum(precisions) / total:.3f} R@{TOP_K}={sum(recalls) / total:.3f} "
        f"MRR={sum(ranks) / total:.3f}\n"
        f"Maior nota por pergunta do assunto: min={min(top_scores):.3f} max={max(top_scores):.3f}\n"
        f"Maior nota fora do assunto: {[round(score, 3) for score in off_topic_scores]}"
    )

    assert sum(recalls) / total >= 0.7
    assert sum(ranks) / total >= 0.6
