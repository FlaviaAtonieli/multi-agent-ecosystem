"""Os comitês de exemplo (scripts/comites_exemplo.json) passam pela API de verdade."""

import importlib.util
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.services.team_context import is_relator
from tests.conftest import register

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
USER = {"name": "Flavia Exemplo", "email": "comites.exemplo@example.com", "password": "StrongPassword!123"}


def _script():
    path = SCRIPTS / "criar_comites_exemplo.py"
    spec = importlib.util.spec_from_file_location("criar_comites_exemplo", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _dados() -> dict:
    return json.loads((SCRIPTS / "comites_exemplo.json").read_text(encoding="utf-8"))


def _plataforma(module, client: TestClient):
    plataforma = module.Plataforma("http://testserver")
    plataforma.client = client
    return plataforma


def test_cada_comite_tem_exatamente_um_relator() -> None:
    for comite in _dados()["comites"]:
        relatores = [a["name"] for a in comite["agentes"] if is_relator(a)]
        assert len(relatores) == 1, (comite["nome"], relatores)


def test_script_cria_os_comites_e_as_skills_pela_api(client: TestClient) -> None:
    module = _script()
    register(client, USER)
    plataforma = _plataforma(module, client)

    module.criar(plataforma, _dados(), USER["email"])

    comites = {c["name"]: c for c in client.get("/api/v1/clans").json()}
    for comite in _dados()["comites"]:
        assert comites[comite["nome"]]["is_open"] is True
        skills = client.get(f"/api/v1/clans/{comites[comite['nome']]['id']}/skills").json()
        assert sorted(s["name"] for s in skills) == sorted(a["name"] for a in comite["agentes"])
        assert sum(is_relator(s["manifest_json"]) for s in skills) == 1


def test_rodar_de_novo_nao_duplica(client: TestClient) -> None:
    module = _script()
    register(client, USER)
    plataforma = _plataforma(module, client)

    module.criar(plataforma, _dados(), USER["email"])
    module.criar(plataforma, _dados(), USER["email"])

    comites = client.get("/api/v1/clans").json()
    assert len(comites) == len(_dados()["comites"])
    for comite in comites:
        skills = client.get(f"/api/v1/clans/{comite['id']}/skills").json()
        assert len(skills) == 5
