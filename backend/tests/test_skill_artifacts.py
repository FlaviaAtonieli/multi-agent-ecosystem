import io
import json
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select

from app.agent_catalog.contracts import (
    AgenteEmissor,
    AnaliseEstruturada,
    ArquivoGerado,
    Governanca,
    SkillToolResult,
)
from app.agent_catalog.tool_interface import SkillExecutor, SkillToolCall
from app.core.config import settings
from app.core.database import SessionLocal
from app.llm.prompts import build_technical_planner_prompt
from app.llm.schemas import LLMPlan, LLMPlanRequest, strict_json_schema
from app.models import AgentSkill, LLMInvocation, TechnicalRequest, User
from app.services import agent_skill_orchestration_service as service
from app.services.artifact_service import (
    MAX_FILE_BYTES,
    MAX_FILES_PER_RESPONSE,
    prepare_files,
    safe_relative_path,
)
from tests.conftest import authenticated_csrf_headers, register
from tests.test_background_orchestration import _start_url, _wait_for_status
from tests.test_clan_orchestration import OTHER, OWNER, _add, _clan, _create_request, _skill, _switch_user


def _headers(client: TestClient) -> dict[str, str]:
    return authenticated_csrf_headers(client)


def _tool_returning(*files: ArquivoGerado):
    async def fake_skill_tool(skill, tool_call) -> SkillToolResult:
        return SkillToolResult(
            trace_id=tool_call.trace_id,
            agente_emissor=AgenteEmissor(nome=skill.name, dominio=skill.domain),
            analise_estruturada=AnaliseEstruturada(resumo_executivo="Resumo da análise."),
            governanca=Governanca(nivel_confianca="ALTO", justificativa_confianca="Evidência suficiente."),
            arquivos=list(files),
        )

    return fake_skill_tool


def _run_with_files(client: TestClient, monkeypatch, *files: ArquivoGerado) -> dict:
    register(client, OWNER)
    clan = _clan(client)
    _add(client, clan["id"], _skill(client, "codigo_legado")["id"])
    request = _create_request(client, clan["id"])
    monkeypatch.setattr(service, "call_skill_tool", _tool_returning(*files))
    assert client.post(_start_url(request["id"]), headers=_headers(client)).status_code == 202
    _wait_for_status(client, request["id"], "COMPLETED", "VALIDATING")
    return request


def _url(request: dict, suffix: str = "") -> str:
    return f"/api/v1/orchestrations/{request['trace_id']}/artifacts{suffix}"


class TestSafePath:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("relatorio.md", "relatorio.md"),
            ("src/app/main.py", "src/app/main.py"),
            ("src\\app\\main.py", "src/app/main.py"),
            ("./src//main.py", "src/main.py"),
            ("  notas.txt  ", "notas.txt"),
        ],
    )
    def test_keeps_project_structure(self, raw: str, expected: str) -> None:
        assert safe_relative_path(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            ".",
            "../segredo.txt",
            "src/../../segredo.txt",
            "..\\..\\segredo.txt",
            "/etc/passwd",
            "\\\\servidor\\arquivo",
            "C:\\Windows\\system.ini",
            "C:relativo.txt",
            "arquivo\x00.txt",
            "linha\nquebrada.txt",
            "a" * 300,
        ],
    )
    def test_rejects_path_that_could_leave_the_folder(self, raw: str) -> None:
        assert safe_relative_path(raw) is None


class TestPrepareFiles:
    def test_rejected_files_are_reported(self) -> None:
        accepted, rejected = prepare_files(
            [
                ArquivoGerado(nome="ok.py", conteudo="print('ok')"),
                ArquivoGerado(nome="../fora.py", conteudo="x"),
                ArquivoGerado(nome="grande.txt", conteudo="x" * (MAX_FILE_BYTES + 1)),
            ]
        )

        assert [item.nome for item in accepted] == ["ok.py"]
        assert rejected == ["../fora.py", "grande.txt"]

    def test_size_is_measured_in_bytes_not_characters(self) -> None:
        accepted, rejected = prepare_files([ArquivoGerado(nome="a.txt", conteudo="é" * MAX_FILE_BYTES)])

        assert accepted == []
        assert rejected == ["a.txt"]

    def test_limits_the_number_of_files(self) -> None:
        files = [ArquivoGerado(nome=f"{i}.txt", conteudo="x") for i in range(MAX_FILES_PER_RESPONSE + 2)]

        accepted, rejected = prepare_files(files)

        assert len(accepted) == MAX_FILES_PER_RESPONSE
        assert len(rejected) == 2

    def test_same_name_twice_keeps_both(self) -> None:
        accepted, _ = prepare_files(
            [ArquivoGerado(nome="a.txt", conteudo="1"), ArquivoGerado(nome="./a.txt", conteudo="2")]
        )

        assert [item.nome for item in accepted] == ["a.txt", "a (2).txt"]

    def test_binary_content_is_rejected(self) -> None:
        accepted, rejected = prepare_files([ArquivoGerado(nome="a.bin", conteudo="a\x00b")])

        assert accepted == []
        assert rejected == ["a.bin"]

    def test_empty_file_is_kept(self) -> None:
        accepted, _ = prepare_files([ArquivoGerado(nome="pacote/__init__.py", conteudo="")])

        assert [item.nome for item in accepted] == ["pacote/__init__.py"]


class TestModelContract:
    def test_schema_for_the_model_is_strict_also_in_nested_objects(self) -> None:
        nested = strict_json_schema(LLMPlan)["$defs"]["LLMGeneratedFile"]

        assert nested["additionalProperties"] is False
        assert sorted(nested["required"]) == ["content", "filename"]

    def test_prompt_only_asks_for_files_when_requested(self) -> None:
        prompt = build_technical_planner_prompt(
            LLMPlanRequest(technical_request_id="1", trace_id="T", title="Título", problem="p", objective="o")
        )

        assert "generated_files" in prompt
        assert "lista vazia" in prompt

    def test_skill_passes_on_the_files_from_the_model(self, client: TestClient, monkeypatch) -> None:
        register(client, OWNER)
        created = _skill(client, "codigo_legado")
        plan = LLMPlan(summary="Resumo.", generated_files=[{"filename": "a.py", "content": "print(1)"}])

        class FakeResponse:
            llm_call_id = "nao-existe"

        response = FakeResponse()
        response.plan = plan
        monkeypatch.setattr(
            "app.agent_catalog.tool_interface.generate_technical_plan", lambda *args, **kwargs: response
        )

        with SessionLocal() as db:
            skill = db.get(AgentSkill, created["id"])
            user = db.scalar(select(User))
            result = SkillExecutor().execute(
                db,
                skill=skill,
                technical_request=TechnicalRequest(id="r", trace_id="TRC"),
                user=user,
                tool_call=SkillToolCall(
                    trace_id="TRC", technical_request_id="r", user_id=user.id, agent_skill_id=skill.id
                ),
            )

        assert result.arquivos == [ArquivoGerado(nome="a.py", conteudo="print(1)")]


class TestApi:
    def test_lists_files_without_their_content(self, client: TestClient, monkeypatch) -> None:
        request = _run_with_files(client, monkeypatch, ArquivoGerado(nome="src/a.py", conteudo="print(1)"))

        listed = client.get(_url(request)).json()

        assert len(listed) == 1
        assert listed[0]["filename"] == "src/a.py"
        assert listed[0]["size_bytes"] == 8
        assert listed[0]["domain"] == "codigo_legado"
        assert "content" not in listed[0]

    def test_response_without_files_has_empty_list(self, client: TestClient, monkeypatch) -> None:
        request = _run_with_files(client, monkeypatch)

        assert client.get(_url(request)).json() == []

    def test_content_is_not_repeated_in_the_skill_result(self, client: TestClient, monkeypatch) -> None:
        request = _run_with_files(client, monkeypatch, ArquivoGerado(nome="a.py", conteudo="CONTEUDO-UNICO"))

        results = client.get(f"/api/v1/orchestrations/{request['trace_id']}/skill-results")

        assert results.status_code == 200
        assert "CONTEUDO-UNICO" not in results.text

    def test_preview_returns_the_text(self, client: TestClient, monkeypatch) -> None:
        request = _run_with_files(client, monkeypatch, ArquivoGerado(nome="a.py", conteudo="print('olá')"))
        artifact_id = client.get(_url(request)).json()[0]["id"]

        response = client.get(_url(request, f"/{artifact_id}"))

        assert response.status_code == 200
        assert response.json()["content"] == "print('olá')"

    def test_download_never_lets_the_browser_run_the_file(self, client: TestClient, monkeypatch) -> None:
        request = _run_with_files(
            client, monkeypatch, ArquivoGerado(nome="pagina.html", conteudo="<script>alert(1)</script>")
        )
        artifact_id = client.get(_url(request)).json()[0]["id"]

        response = client.get(_url(request, f"/{artifact_id}/download"))

        assert response.status_code == 200
        assert response.content == b"<script>alert(1)</script>"
        assert response.headers["content-type"].startswith("application/octet-stream")
        assert response.headers["content-disposition"].startswith("attachment")
        assert "pagina.html" in response.headers["content-disposition"]
        assert response.headers["x-content-type-options"] == "nosniff"

    def test_download_keeps_accented_file_name(self, client: TestClient, monkeypatch) -> None:
        request = _run_with_files(client, monkeypatch, ArquivoGerado(nome="relatório.md", conteudo="x"))
        artifact_id = client.get(_url(request)).json()[0]["id"]

        response = client.get(_url(request, f"/{artifact_id}/download"))

        assert response.status_code == 200
        assert "relat%C3%B3rio.md" in response.headers["content-disposition"]

    def test_zip_keeps_structure_and_separates_skills(self, client: TestClient, monkeypatch) -> None:
        request = _run_with_files(
            client,
            monkeypatch,
            ArquivoGerado(nome="src/a.py", conteudo="print(1)"),
            ArquivoGerado(nome="README.md", conteudo="# Projeto"),
        )

        response = client.get(_url(request, ".zip"))

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert request["trace_id"] in response.headers["content-disposition"]
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names = archive.namelist()
            assert all(name.split("/")[0] == "codigo_legado" for name in names)
            assert sorted(names) == ["codigo_legado/README.md", "codigo_legado/src/a.py"]
            assert archive.read("codigo_legado/src/a.py") == b"print(1)"

    def test_zip_without_files_is_not_found(self, client: TestClient, monkeypatch) -> None:
        request = _run_with_files(client, monkeypatch)

        assert client.get(_url(request, ".zip")).status_code == 404

    def test_unsafe_file_is_not_stored_and_timeline_tells(self, client: TestClient, monkeypatch) -> None:
        request = _run_with_files(
            client,
            monkeypatch,
            ArquivoGerado(nome="../fora.py", conteudo="x"),
            ArquivoGerado(nome="dentro.py", conteudo="y"),
        )

        assert [item["filename"] for item in client.get(_url(request)).json()] == ["dentro.py"]
        events = client.get(f"/api/v1/orchestrations/{request['trace_id']}").json()["events"]
        completed = next(e for e in events if e["event_type"] == "AGENT_SKILL_INVOCATION_COMPLETED")
        assert completed["payload"]["artifacts_stored"] == 1
        assert completed["payload"]["artifacts_rejected"] == ["../fora.py"]

    @pytest.mark.parametrize("suffix", ["", ".zip", "/{id}", "/{id}/download"])
    def test_other_person_cannot_read(self, client: TestClient, monkeypatch, suffix: str) -> None:
        request = _run_with_files(client, monkeypatch, ArquivoGerado(nome="a.py", conteudo="x"))
        artifact_id = client.get(_url(request)).json()[0]["id"]
        _switch_user(client, OTHER)

        assert client.get(_url(request, suffix.replace("{id}", artifact_id))).status_code == 404

    def test_file_of_another_orchestration_is_not_found(self, client: TestClient, monkeypatch) -> None:
        first = _run_with_files(client, monkeypatch, ArquivoGerado(nome="a.py", conteudo="x"))
        artifact_id = client.get(_url(first)).json()[0]["id"]
        clan = _clan(client)
        other_request = _create_request(client, clan["id"])

        assert client.get(_url(other_request, f"/{artifact_id}")).status_code == 404

    def test_showing_files_does_not_call_the_model(self, client: TestClient, monkeypatch) -> None:
        request = _run_with_files(client, monkeypatch, ArquivoGerado(nome="a.py", conteudo="x"))

        def must_not_run(*args, **kwargs):
            raise AssertionError("Mostrar arquivos não pode chamar o modelo.")

        monkeypatch.setattr("app.services.llm_service.generate_technical_plan", must_not_run)
        monkeypatch.setattr("app.agent_catalog.tool_interface.generate_technical_plan", must_not_run)
        monkeypatch.setattr(service, "call_skill_tool", must_not_run)
        with SessionLocal() as db:
            before = db.scalar(select(func.count(LLMInvocation.id)))

        artifact_id = client.get(_url(request)).json()[0]["id"]
        assert client.get(_url(request, f"/{artifact_id}")).status_code == 200
        assert client.get(_url(request, f"/{artifact_id}/download")).status_code == 200
        assert client.get(_url(request, ".zip")).status_code == 200

        with SessionLocal() as db:
            assert db.scalar(select(func.count(LLMInvocation.id))) == before

    def test_follow_up_files_are_kept_too(self, client: TestClient, monkeypatch) -> None:
        request = _run_with_files(client, monkeypatch, ArquivoGerado(nome="primeiro.py", conteudo="1"))
        monkeypatch.setattr(
            service, "call_skill_tool", _tool_returning(ArquivoGerado(nome="segundo.py", conteudo="2"))
        )

        response = client.post(
            f"/api/v1/agent-skills/requests/{request['id']}/ask/start",
            json={"question": "Gere o segundo arquivo."},
            headers=_headers(client),
        )
        assert response.status_code == 202
        deadline_files: list[str] = []
        for _ in range(200):
            deadline_files = [item["filename"] for item in client.get(_url(request)).json()]
            if "segundo.py" in deadline_files:
                break
            time.sleep(0.05)

        assert sorted(deadline_files) == ["primeiro.py", "segundo.py"]


def test_files_cross_the_real_mcp_process_boundary(client: TestClient, monkeypatch) -> None:
    """Tudo real, menos a OpenRouter: o servidor MCP roda em outro processo, e um servidor
    local responde no lugar do provedor, com um arquivo grande no JSON do modelo."""
    big_file = "x = 1\n" * 40_000
    requests_seen: list[dict] = []

    class FakeOpenRouter(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:
            pass

        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            requests_seen.append(body)
            plan = {
                "summary": "Resumo.",
                "required_agents": [],
                "required_skills": [],
                "risks": [],
                "missing_information": [],
                "requires_human_approval": True,
                "generated_files": [
                    {"filename": "src/grande.py", "content": big_file},
                    {"filename": "../fora.py", "content": "x"},
                ],
            }
            raw = json.dumps(
                {
                    "id": "gen-teste",
                    "object": "chat.completion",
                    "created": 1,
                    "model": body["model"],
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": json.dumps(plan)},
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenRouter)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        monkeypatch.setattr(settings, "llm_enabled", True)
        monkeypatch.setattr(settings, "llm_provider", "openrouter")
        monkeypatch.setattr(settings, "llm_model", "fake/modelo")
        monkeypatch.setattr(settings, "llm_allowed_models", "fake/modelo")
        monkeypatch.setattr(settings, "openrouter_api_key", SecretStr("chave-falsa"))
        monkeypatch.setattr(settings, "openrouter_base_url", f"http://127.0.0.1:{server.server_port}/api/v1")
        monkeypatch.setattr(settings, "rag_enabled", False)
        monkeypatch.setattr(settings, "mcp_skill_transport", "stdio")

        register(client, OWNER)
        clan = _clan(client)
        _add(client, clan["id"], _skill(client, "codigo_legado")["id"])
        request = _create_request(client, clan["id"])
        assert client.post(_start_url(request["id"]), headers=_headers(client)).status_code == 202
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            status = client.get(f"/api/v1/requests/{request['id']}").json()["status"]
            if status in {"COMPLETED", "VALIDATING", "FAILED"}:
                break
            time.sleep(0.2)
        assert status in {"COMPLETED", "VALIDATING"}

        listed = client.get(_url(request)).json()
        assert [item["filename"] for item in listed] == ["src/grande.py"]
        content = client.get(_url(request, f"/{listed[0]['id']}")).json()["content"]
        assert content == big_file

        schema = requests_seen[0]["response_format"]["json_schema"]["schema"]
        assert schema["$defs"]["LLMGeneratedFile"]["additionalProperties"] is False
        assert "generated_files" in schema["required"]
    finally:
        server.shutdown()
