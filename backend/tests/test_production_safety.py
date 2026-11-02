import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select

from app.agent_catalog.mcp_client import _module_for_skill
from app.core.config import settings
from app.core.database import SessionLocal
from app.db.seed_agent_skills import seed_agent_skills
from app.models import AgentSkill
from app.schemas.user import UserCreate
from app.services.email_service import console_outbox, send_email
from tests.conftest import register

USER = {
    "name": "Conta Inicial",
    "email": "conta.inicial@example.com",
    "password": "StrongPassword!123",
}


def test_rejected_password_is_not_in_the_validation_error() -> None:
    with pytest.raises(ValidationError) as error:
        UserCreate(name="Conta Inicial", email="conta@example.com", password="Fl@curta")

    assert "Fl@curta" not in str(error.value)


def test_console_email_body_is_not_logged_in_production(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "email_backend", "console")
    console_outbox.clear()

    with caplog.at_level(logging.WARNING):
        send_email(to="a@example.com", subject="Redefinir senha", body="https://site/reset?token=segredo")

    assert "não enviado" in caplog.text
    assert "segredo" not in caplog.text
    console_outbox.clear()


def test_console_email_body_is_logged_outside_production(monkeypatch, caplog) -> None:
    monkeypatch.setattr(settings, "email_backend", "console")
    console_outbox.clear()

    with caplog.at_level(logging.WARNING):
        send_email(to="a@example.com", subject="Código", body="Seu código é 123456")

    assert "123456" in caplog.text
    console_outbox.clear()


def test_default_model_is_allowed() -> None:
    assert settings.llm_model in settings.llm_allowed_model_list


def test_seed_registers_all_domains_once_on_the_right_servers(client: TestClient, monkeypatch) -> None:
    register(client, USER)
    monkeypatch.setattr(settings, "bootstrap_admin_email", USER["email"])

    seed_agent_skills()
    seed_agent_skills()

    with SessionLocal() as db:
        assert db.scalar(select(func.count(AgentSkill.id))) == 10
        skills = {skill.domain: skill for skill in db.scalars(select(AgentSkill))}

    assert _module_for_skill(skills["seguranca_informacao"]).endswith("security_server")
    assert skills["seguranca_informacao"].owner_id is None
    assert _module_for_skill(skills["apis_integracoes"]).endswith("generic_skill_server")
    assert all(skill.visibility == "OFFICIAL" and skill.enabled for skill in skills.values())
