"""Primeira camada da validação de contexto: regras fixas, sem IA e sem custo.

Barra textos que passam do tamanho mínimo sem descrever nada (TESTE TESTE...,
teclado batido, texto colado repetido) antes de qualquer orquestração.
"""

import pytest
from fastapi.testclient import TestClient

from app.services.context_quality import context_issues, describes_something
from tests.conftest import authenticated_csrf_headers, create_test_clan, register

SEM_CONTEUDO = [
    "TESTE " * 12,
    "teste teste teste teste teste teste teste teste",
    "teste test testando testes lorem ipsum asdf qwerty 123 abc",
    "asdfasdf qwerqwer zxcvzxcv kkkkkkk hahahaha sdfghjkl",
    "a" * 60,
    "1234567890 1234567890 1234567890 1234567890",
    "lorem ipsum dolor sit amet lorem ipsum dolor sit amet foo bar",
    "O job demora muito no processamento. " * 4,
    "...................................................",
]

COM_CONTEUDO = [
    "Sistema legado em Java. O job chama o repositório para cada cliente.",
    "API REST em Java 17 com Spring Boot, banco Oracle e job batch noturno.",
    "Teste de integração do sistema de pagamento falhando desde a versão 2.3.",
    "A integração ocorre entre o módulo de estoque e a API de compras. "
    "O retorno esperado contém oito sequências, mas apenas quatro são exibidas.",
    "Migração do COBOL para .NET 8; o módulo CRM usa DB2 e OAuth2 no gateway HTTP.",
]


@pytest.mark.parametrize("text", SEM_CONTEUDO)
def test_texto_sem_conteudo_e_barrado(text: str) -> None:
    assert context_issues(text), text


@pytest.mark.parametrize("text", COM_CONTEUDO)
def test_contexto_real_passa(text: str) -> None:
    assert context_issues(text) == []


def test_texto_curto_explica_o_minimo() -> None:
    issues = context_issues("Java e Oracle")
    assert any("40 caracteres" in issue for issue in issues)


def test_texto_repetido_explica_a_repeticao() -> None:
    issues = context_issues("O job demora muito no processamento. " * 4)
    assert any("se repete" in issue for issue in issues)


def test_vazio_ou_nulo() -> None:
    assert context_issues(None)
    assert context_issues("   ")


def _create(client: TestClient, context: str) -> dict:
    register(
        client,
        {"name": "Conta Contexto", "email": "contexto@example.com", "password": "StrongPassword!123"},
    )
    response = client.post(
        "/api/v1/requests",
        json={
            "title": "Analisar integração corporativa",
            "problem": "A API atual apresenta inconsistência entre contrato e retorno.",
            "objective": "Mapear o impacto técnico e orientar a correção.",
            "context": context,
            "clan_id": create_test_clan(client),
        },
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 201
    return response.json()


def _context_requested(client: TestClient, trace_id: str) -> dict:
    events = client.get(f"/api/v1/orchestrations/{trace_id}").json()["events"]
    return [event for event in events if event["event_type"] == "CONTEXT_REQUESTED"][-1]


def test_solicitacao_com_teste_repetido_fica_aguardando_contexto(client: TestClient) -> None:
    created = _create(client, "TESTE " * 12)

    assert created["status"] == "AWAITING_CONTEXT"
    event = _context_requested(client, created["trace_id"])
    assert event["payload"]["issues"]
    assert "palavras" in event["message"]


def test_complementar_com_lixo_continua_aguardando(client: TestClient) -> None:
    created = _create(client, "Curto")

    response = client.post(
        f"/api/v1/requests/{created['id']}/context",
        json={"context": "asdfasdf qwerqwer zxcvzxcv kkkkkkk hahahaha sdfghjkl"},
        headers=authenticated_csrf_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "AWAITING_CONTEXT"
    assert _context_requested(client, created["trace_id"])["payload"]["issues"]


def test_complementar_com_contexto_real_qualifica(client: TestClient) -> None:
    created = _create(client, "TESTE " * 12)

    response = client.post(
        f"/api/v1/requests/{created['id']}/context",
        json={"context": COM_CONTEUDO[0]},
        headers=authenticated_csrf_headers(client),
    )

    assert response.json()["status"] == "QUALIFIED"


# --- Problema e objetivo -----------------------------------------------------
# Só o contexto pode ser complementado depois. Problema e objetivo sem conteúdo
# são recusados já no cadastro, com o motivo, para a pessoa corrigir no form.


@pytest.mark.parametrize(
    "text", ["TESTE TESTE TESTE", "asdfasdf qwerqwer", "teste teste teste teste", "1234567890"]
)
def test_problema_sem_conteudo_nao_descreve_nada(text: str) -> None:
    assert not describes_something(text)


@pytest.mark.parametrize(
    "text", ["O job demora.", "Reduzir o tempo.", "Erro de timeout na API", "Teste de carga falhando"]
)
def test_problema_curto_mas_real_descreve(text: str) -> None:
    assert describes_something(text)


@pytest.mark.parametrize("field", ["problem", "objective"])
def test_cadastro_recusa_problema_ou_objetivo_sem_conteudo(client: TestClient, field: str) -> None:
    register(
        client,
        {"name": "Conta Campos", "email": f"campos-{field}@example.com", "password": "StrongPassword!123"},
    )
    payload = {
        "title": "Analisar integração corporativa",
        "problem": "A API atual apresenta inconsistência entre contrato e retorno.",
        "objective": "Mapear o impacto técnico e orientar a correção.",
        "context": COM_CONTEUDO[0],
        "clan_id": create_test_clan(client),
    }
    payload[field] = "TESTE TESTE TESTE TESTE"

    response = client.post("/api/v1/requests", json=payload, headers=authenticated_csrf_headers(client))

    assert response.status_code == 422
    detail = next(item for item in response.json()["details"] if item["field"] == field)
    assert detail["message"].startswith("Descreva")
    assert "Value error" not in detail["message"]
