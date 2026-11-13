"""Repositório do GitHub como base de conhecimento de um comitê (fase 1).

O GitHub é imitado por um servidor local, e os embeddings por um vetor de palavras:
sem rede e sem custo, mas com download, extração e busca de verdade.
"""

import io
import json
import tarfile
import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import AuditLog, ClanRepository, KnowledgeChunk
from app.rag.retriever import InMemoryVectorRetriever
from app.services import repository_service
from app.services.repository_service import InvalidRepositoryUrl, fail_interrupted_indexing, parse_github_url
from tests.conftest import authenticated_csrf_headers, register
from tests.test_clan_orchestration import OTHER, OWNER, _clan, _switch_user
from tests.test_skill_suggestions import WordCountEmbeddings

ROOT = "acme-faturamento-abc1234"
FILES = {
    f"{ROOT}/README.md": b"# Faturamento\nCalcula juros de parcelas atrasadas.",
    f"{ROOT}/src/juros.py": b"def calcular_juros(parcela, dias):\n    return parcela * 0.01 * dias\n",
    f"{ROOT}/src/app.ts": b"import { calcularJuros } from './juros'\nexport const total = 1\n",
    f"{ROOT}/node_modules/lib/index.js": b"module.exports = 'nao deve entrar'",
    f"{ROOT}/assets/logo.png": b"\x89PNG\r\n\x1a\n\x00\x00binario",
    f"{ROOT}/dados.bin": b"\x00\x01\x02",
}


def _tarball(files: dict[str, bytes], *, symlink: bool = False, escape: bool = False) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        if symlink:
            link = tarfile.TarInfo(f"{ROOT}/link.py")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            tar.addfile(link)
        if escape:
            evil = tarfile.TarInfo("../../fora.py")
            payload = b"segredo = 1"
            evil.size = len(payload)
            tar.addfile(evil, io.BytesIO(payload))
    return buffer.getvalue()


class FakeGitHub:
    def __init__(self) -> None:
        self.repos: dict[str, dict] = {}
        self.tarballs: dict[str, bytes] = {}
        self.requests: list[str] = []

    def add(self, full_name: str, tarball: bytes, *, size_kb: int = 10, private: bool = False) -> None:
        self.repos[full_name] = {"default_branch": "main", "size": size_kb, "private": private}
        self.tarballs[full_name] = tarball


@pytest.fixture
def github(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeGitHub]:
    fake = FakeGitHub()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:
            pass

        def do_GET(self) -> None:
            fake.requests.append(self.path)
            parts = self.path.strip("/").split("/")
            full_name = "/".join(parts[1:3]) if len(parts) >= 3 else ""
            if parts[0] != "repos" or full_name not in fake.repos or fake.repos[full_name]["private"]:
                self.send_response(404)
                self.end_headers()
                return
            if len(parts) == 3:
                body = json.dumps(fake.repos[full_name]).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
            else:
                body = fake.tarballs[full_name]
                self.send_response(200)
                self.send_header("Content-Type", "application/x-gzip")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(settings, "github_api_base_url", f"http://127.0.0.1:{server.server_port}")
    try:
        yield fake
    finally:
        server.shutdown()


@pytest.fixture
def embeddings(monkeypatch: pytest.MonkeyPatch) -> WordCountEmbeddings:
    fake = WordCountEmbeddings()
    monkeypatch.setattr(repository_service, "create_embedding_provider", lambda config: fake)
    return fake


def _headers(client: TestClient) -> dict[str, str]:
    return authenticated_csrf_headers(client)


def _url(clan_id: str, suffix: str = "") -> str:
    return f"/api/v1/clans/{clan_id}/repositories{suffix}"


def _add(client: TestClient, clan_id: str, url: str = "https://github.com/acme/faturamento"):
    return client.post(_url(clan_id), json={"url": url}, headers=_headers(client))


def _wait(client: TestClient, clan_id: str, repo_id: str, *expected: str) -> dict:
    deadline = time.monotonic() + 10
    body: dict = {}
    while time.monotonic() < deadline:
        body = next(item for item in client.get(_url(clan_id)).json() if item["id"] == repo_id)
        if body["status"] in expected:
            return body
        time.sleep(0.05)
    raise AssertionError(f"Repositório não chegou a {expected}; último status: {body.get('status')}")


def _indexed(client: TestClient, github: FakeGitHub, **tar_options) -> tuple[dict, dict]:
    register(client, OWNER)
    clan = _clan(client)
    github.add("acme/faturamento", _tarball(FILES, **tar_options))
    response = _add(client, clan["id"])
    assert response.status_code == 201, response.text
    return clan, _wait(client, clan["id"], response.json()["id"], "READY", "FAILED")


def _chunks(repository_id: str) -> list[KnowledgeChunk]:
    with SessionLocal() as db:
        return list(db.scalars(select(KnowledgeChunk).where(KnowledgeChunk.repository_id == repository_id)))


class TestParseUrl:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://github.com/acme/faturamento", ("acme", "faturamento")),
            ("https://github.com/acme/faturamento.git", ("acme", "faturamento")),
            ("https://github.com/acme/faturamento/", ("acme", "faturamento")),
            ("  https://github.com/Acme-Corp/meu.repo  ", ("Acme-Corp", "meu.repo")),
        ],
    )
    def test_aceita_repositorio_do_github(self, url: str, expected: tuple[str, str]) -> None:
        assert parse_github_url(url) == expected

    @pytest.mark.parametrize(
        "url",
        [
            "http://github.com/acme/faturamento",
            "https://gitlab.com/acme/faturamento",
            "https://github.com.evil.com/acme/faturamento",
            "git@github.com:acme/faturamento.git",
            "https://github.com/acme",
            "https://github.com/acme/faturamento/tree/main",
            "https://user:token@github.com/acme/faturamento",
            "https://github.com/../faturamento",
        ],
    )
    def test_recusa_o_resto(self, url: str) -> None:
        with pytest.raises(InvalidRepositoryUrl):
            parse_github_url(url)


def test_indexa_so_os_arquivos_de_texto_do_codigo(client: TestClient, github: FakeGitHub, embeddings) -> None:
    _, repository = _indexed(client, github, symlink=True, escape=True)

    assert repository["status"] == "READY"
    assert repository["file_count"] == 3
    names = {chunk.artifact_name for chunk in _chunks(repository["id"])}
    assert names == {
        "acme/faturamento:README.md",
        "acme/faturamento:src/juros.py",
        "acme/faturamento:src/app.ts",
    }
    assert repository["chunk_count"] == len(_chunks(repository["id"]))
    assert repository["indexed_at"] is not None


def test_busca_do_comite_encontra_o_codigo_e_outro_comite_nao(
    client: TestClient, github: FakeGitHub, embeddings
) -> None:
    clan, _ = _indexed(client, github)
    other_clan = _clan(client)

    with SessionLocal() as db:
        retriever = InMemoryVectorRetriever(db, embeddings)
        inside = retriever.retrieve("calcular juros parcela dias", top_k=3, clan_id=clan["id"])
        outside = retriever.retrieve("calcular juros parcela dias", top_k=3, clan_id=other_clan["id"])
        global_only = retriever.retrieve("calcular juros parcela dias", top_k=3)

    assert inside[0].artifact_name == "acme/faturamento:src/juros.py"
    assert all(not chunk.artifact_name.startswith("acme/") for chunk in outside)
    assert all(not chunk.artifact_name.startswith("acme/") for chunk in global_only)


def test_repositorio_privado_ou_inexistente_falha_com_motivo(
    client: TestClient, github: FakeGitHub, embeddings
) -> None:
    register(client, OWNER)
    clan = _clan(client)
    github.add("acme/segredo", _tarball(FILES), private=True)

    response = _add(client, clan["id"], "https://github.com/acme/segredo")
    repository = _wait(client, clan["id"], response.json()["id"], "READY", "FAILED")

    assert repository["status"] == "FAILED"
    assert "não foi encontrado ou é privado" in repository["error_message"]
    assert _chunks(repository["id"]) == []


def test_repositorio_grande_demais_nem_e_baixado(
    client: TestClient, github: FakeGitHub, embeddings, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "repository_max_download_mb", 1)
    register(client, OWNER)
    clan = _clan(client)
    github.add("acme/gigante", _tarball(FILES), size_kb=50_000)

    response = _add(client, clan["id"], "https://github.com/acme/gigante")
    repository = _wait(client, clan["id"], response.json()["id"], "READY", "FAILED")

    assert repository["status"] == "FAILED"
    assert "maior que o limite" in repository["error_message"]
    assert not any("tarball" in path for path in github.requests)


def test_limite_de_arquivos(client: TestClient, github: FakeGitHub, embeddings, monkeypatch) -> None:
    monkeypatch.setattr(settings, "repository_max_files", 2)

    _, repository = _indexed(client, github)

    assert repository["status"] == "READY"
    assert repository["file_count"] == 2


def test_url_invalida_e_recusada_na_hora(client: TestClient, github: FakeGitHub, embeddings) -> None:
    register(client, OWNER)
    clan = _clan(client)

    response = _add(client, clan["id"], "https://gitlab.com/acme/faturamento")

    assert response.status_code == 422
    assert github.requests == []


def test_mesmo_repositorio_duas_vezes_no_comite(client: TestClient, github: FakeGitHub, embeddings) -> None:
    clan, _ = _indexed(client, github)

    assert _add(client, clan["id"], "https://github.com/acme/faturamento.git").status_code == 409


def test_quem_nao_e_membro_nao_adiciona_nem_ve(client: TestClient, github: FakeGitHub, embeddings) -> None:
    clan, _ = _indexed(client, github)
    client.post("/api/v1/auth/register", json=OTHER, headers=_headers(client))
    _switch_user(client, OTHER)

    assert _add(client, clan["id"], "https://github.com/acme/outro").status_code == 403
    assert client.get(_url(clan["id"])).status_code == 403


def test_remover_apaga_os_trechos(client: TestClient, github: FakeGitHub, embeddings) -> None:
    clan, repository = _indexed(client, github)

    response = client.delete(_url(clan["id"], f"/{repository['id']}"), headers=_headers(client))

    assert response.status_code == 204
    assert client.get(_url(clan["id"])).json() == []
    with SessionLocal() as db:
        remaining = db.scalar(
            select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.artifact_name.like("acme/%"))
        )
    assert remaining == 0


def test_reindexar_troca_os_trechos_sem_duplicar(client: TestClient, github: FakeGitHub, embeddings) -> None:
    clan, repository = _indexed(client, github)
    before = len(_chunks(repository["id"]))
    github.add("acme/faturamento", _tarball({f"{ROOT}/src/juros.py": FILES[f"{ROOT}/src/juros.py"]}))

    response = client.post(_url(clan["id"], f"/{repository['id']}/reindex"), headers=_headers(client))
    assert response.status_code == 202
    time.sleep(0.1)
    repository = _wait(client, clan["id"], repository["id"], "READY", "FAILED")

    assert repository["file_count"] == 1
    assert 0 < len(_chunks(repository["id"])) < before


def test_auditoria_registra_adicao_e_remocao(client: TestClient, github: FakeGitHub, embeddings) -> None:
    clan, repository = _indexed(client, github)
    client.delete(_url(clan["id"], f"/{repository['id']}"), headers=_headers(client))

    with SessionLocal() as db:
        events = set(
            db.scalars(select(AuditLog.event_type).where(AuditLog.event_type.like("CLAN_REPOSITORY_%")))
        )
    assert events == {"CLAN_REPOSITORY_ADDED", "CLAN_REPOSITORY_REMOVED"}


def test_indexacao_interrompida_por_reinicio_vira_falha(client: TestClient) -> None:
    register(client, OWNER)
    clan = _clan(client)
    with SessionLocal() as db:
        repository = ClanRepository(
            clan_id=clan["id"],
            owner="acme",
            name="parado",
            url="https://github.com/acme/parado",
            status="INDEXING",
            added_by_id=db.scalar(select(AuditLog.user_id).limit(1)),
        )
        db.add(repository)
        db.commit()
        repository_id = repository.id

    with SessionLocal() as db:
        assert fail_interrupted_indexing(db) == 1

    with SessionLocal() as db:
        stored = db.get(ClanRepository, repository_id)
        assert stored is not None
        assert stored.status == "FAILED"
        assert "reiniciou" in (stored.error_message or "")


def test_contexto_da_orquestracao_usa_o_repositorio_do_comite_da_solicitacao(
    client: TestClient, github: FakeGitHub, embeddings, monkeypatch
) -> None:
    from types import SimpleNamespace

    from app.llm.schemas import LLMPlanRequest
    from app.rag import factory
    from app.rag.service import retrieve_context_for_request

    clan, _ = _indexed(client, github)
    other_clan = _clan(client)
    monkeypatch.setattr(factory, "create_embedding_provider", lambda config: embeddings)
    monkeypatch.setattr(settings, "rag_enabled", True)
    safe_request = LLMPlanRequest(
        technical_request_id="req-1",
        trace_id="TRC-1",
        title="Juros errados",
        problem="calcular juros parcela dias",
        objective="Corrigir o cálculo de juros.",
    )

    with SessionLocal() as db:
        inside = retrieve_context_for_request(db, SimpleNamespace(clan_id=clan["id"]), safe_request)
        outside = retrieve_context_for_request(db, SimpleNamespace(clan_id=other_clan["id"]), safe_request)

    assert any(chunk.artifact_name.startswith("acme/faturamento:") for chunk in inside.chunks)
    assert not any(chunk.artifact_name.startswith("acme/") for chunk in outside.chunks)


def test_pacote_que_descompacta_demais_e_recusado(monkeypatch) -> None:
    from app.services.repository_service import RepositoryIndexingError, read_text_files

    monkeypatch.setattr(settings, "repository_max_download_mb", 1)
    # 12 MB de zeros compactam para poucos KB, mas passam de 10 vezes o limite de 1 MB.
    archive = _tarball({f"{ROOT}/grande.txt": b"0" * (12 * 1024 * 1024)})
    assert len(archive) < 1024 * 1024

    with pytest.raises(RepositoryIndexingError, match="descompactado"):
        read_text_files(archive, settings)
