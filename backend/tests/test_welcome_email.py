"""E-mail de conta criada: vai para todo cadastro novo e nunca bloqueia o cadastro."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.services import welcome_email_service
from app.services.email_service import EmailDeliveryError, console_outbox
from tests.conftest import csrf_headers, register
from tests.test_github_oauth import _enable_github_oauth, _start_github_login, _stub_github_profile
from tests.test_google_oauth import _enable_google_oauth, _start_google_login, _stub_google_profile

USER = {"name": "Pessoa Nova", "email": "pessoa.nova@example.com", "password": "StrongPassword!123"}


@pytest.fixture(autouse=True)
def _console_email(monkeypatch) -> None:
    monkeypatch.setattr(settings, "email_backend", "console")
    console_outbox.clear()
    yield
    console_outbox.clear()


def _welcome_messages(to: str) -> list:
    return [m for m in console_outbox if m["To"] == to and "conta" in m["Subject"].lower()]


def test_cadastro_envia_email_de_conta_criada(client: TestClient) -> None:
    register(client, USER)

    messages = _welcome_messages(USER["email"])
    assert len(messages) == 1
    body = messages[0].get_content()
    assert USER["name"] in body
    assert settings.frontend_base_url in body
    # Avisa quem não pediu a conta: alguém pode ter usado o e-mail de outra pessoa.
    assert "Se não foi você" in body
    assert USER["password"] not in body


def test_falha_no_envio_nao_impede_o_cadastro(client: TestClient, monkeypatch) -> None:
    def broken(**_kwargs) -> None:
        raise EmailDeliveryError("SMTP fora do ar")

    monkeypatch.setattr(welcome_email_service, "send_email", broken)

    response = client.post("/api/v1/auth/register", json=USER, headers=csrf_headers(client))

    assert response.status_code == 201


def test_cadastro_recusado_nao_envia_email(client: TestClient) -> None:
    register(client, USER)
    console_outbox.clear()

    response = client.post("/api/v1/auth/register", json=USER, headers=csrf_headers(client))

    assert response.status_code == 409
    assert _welcome_messages(USER["email"]) == []


def test_cadastro_pelo_github_tambem_envia(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "login_email_code_enabled", False)
    _enable_github_oauth(monkeypatch)
    _stub_github_profile(monkeypatch, email="dev.novo@example.com")
    state = _start_github_login(client)

    client.get(f"/api/v1/auth/github/callback?code=abc&state={state}", follow_redirects=False)

    assert len(_welcome_messages("dev.novo@example.com")) == 1


def test_login_pelo_github_de_conta_existente_nao_reenvia(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "login_email_code_enabled", False)
    _enable_github_oauth(monkeypatch)
    _stub_github_profile(monkeypatch, email="dev.novo@example.com")
    for _ in range(2):
        state = _start_github_login(client)
        client.get(f"/api/v1/auth/github/callback?code=abc&state={state}", follow_redirects=False)

    assert len(_welcome_messages("dev.novo@example.com")) == 1


def test_cadastro_pelo_google_tambem_envia(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "login_email_code_enabled", False)
    _enable_google_oauth(monkeypatch)
    _stub_google_profile(monkeypatch, email="nova.google@example.com")
    state = _start_google_login(client)

    client.get(
        "/api/v1/auth/google/callback",
        params={"code": "fake-code", "state": state},
        follow_redirects=False,
    )

    assert len(_welcome_messages("nova.google@example.com")) == 1


def test_cadastro_com_codigo_de_login_tambem_envia(client: TestClient, monkeypatch) -> None:
    # Navegador novo: o GitHub cria a conta e manda para o código de acesso.
    monkeypatch.setattr(settings, "login_email_code_enabled", True)
    _enable_github_oauth(monkeypatch)
    _stub_github_profile(monkeypatch, email="dev.codigo@example.com")
    state = _start_github_login(client)

    client.get(f"/api/v1/auth/github/callback?code=abc&state={state}", follow_redirects=False)

    assert len(_welcome_messages("dev.codigo@example.com")) == 1


def test_recuperar_senha_sem_email_configurado_em_producao_avisa(client: TestClient, monkeypatch) -> None:
    # Antes, a tela dizia "você vai receber um link" e nada era enviado.
    register(client, USER)
    monkeypatch.setattr(settings, "environment", "production")

    for email in (USER["email"], "nao.existe@example.com"):
        response = client.post(
            "/api/v1/auth/password/forgot", json={"email": email}, headers=csrf_headers(client)
        )
        # Mesma resposta exista ou não a conta: continua sem revelar e-mails cadastrados.
        assert response.status_code == 503
        assert "não está configurad" in response.json()["message"]
