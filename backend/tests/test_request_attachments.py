from fastapi.testclient import TestClient

from app.core.config import settings
from tests.conftest import authenticated_csrf_headers, create_qualified_request, register

OWNER = {
    "name": "Dona da Solicitacao",
    "email": "dona.anexo@example.com",
    "password": "StrongPassword!123",
}
OTHER_USER = {
    "name": "Outra Usuaria",
    "email": "outra.anexo@example.com",
    "password": "StrongPassword!123",
}


def _upload(
    client: TestClient,
    request_id: str,
    filename: str,
    content: bytes,
    content_type: str = "text/plain",
):
    return client.post(
        f"/api/v1/requests/{request_id}/attachments",
        files={"file": (filename, content, content_type)},
        headers=authenticated_csrf_headers(client),
    )


def test_upload_and_list_attachment(client: TestClient) -> None:
    register(client, OWNER)
    technical_request = create_qualified_request(client)

    response = _upload(client, technical_request["id"], "notas.txt", b"Conteudo de teste do anexo.")
    assert response.status_code == 201
    payload = response.json()
    assert payload["filename"] == "notas.txt"
    assert payload["size_bytes"] == len(b"Conteudo de teste do anexo.")
    # Content itself isn't part of the read schema -- keeps the list payload small.
    assert "content" not in payload

    listed = client.get(
        f"/api/v1/requests/{technical_request['id']}/attachments",
        headers=authenticated_csrf_headers(client),
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == payload["id"]


def test_upload_rejects_disallowed_extension(client: TestClient) -> None:
    register(client, OWNER)
    technical_request = create_qualified_request(client)

    response = _upload(client, technical_request["id"], "malicioso.exe", b"conteudo qualquer")
    assert response.status_code == 422
    assert "Extensões aceitas" in response.json()["message"]


def test_upload_rejects_oversized_file(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "attachment_max_bytes", 100)
    register(client, OWNER)
    technical_request = create_qualified_request(client)

    response = _upload(client, technical_request["id"], "grande.txt", b"x" * 200)
    assert response.status_code == 422
    assert "tamanho máximo" in response.json()["message"]


def test_upload_rejects_empty_file(client: TestClient) -> None:
    register(client, OWNER)
    technical_request = create_qualified_request(client)

    response = _upload(client, technical_request["id"], "vazio.txt", b"")
    assert response.status_code == 422
    assert "vazio" in response.json()["message"]


def test_upload_rejects_non_utf8_content(client: TestClient) -> None:
    register(client, OWNER)
    technical_request = create_qualified_request(client)

    # 0xff 0xfe is not valid standalone UTF-8.
    response = _upload(client, technical_request["id"], "binario.txt", b"\xff\xfe\x00\x01")
    assert response.status_code == 422
    assert "UTF-8" in response.json()["message"]


def test_attachment_never_qualifies_a_request_by_itself(client: TestClient) -> None:
    """Orthogonal to complement_context on purpose (see add_attachment's
    docstring): a request created with too little freeform context stays
    AWAITING_CONTEXT even after a document is attached -- otherwise a single
    tiny file would silently bypass the minimum-context qualification rule."""
    register(client, OWNER)
    response = client.post(
        "/api/v1/requests",
        json={
            "title": "Investigar lentidão no checkout",
            "problem": "O checkout está lento em horários de pico.",
            "objective": "Entender a causa raiz.",
            "context": "pouco",
            "restrictions": [],
            "requested_domains": [],
        },
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 201
    technical_request = response.json()
    assert technical_request["status"] == "AWAITING_CONTEXT"

    upload = _upload(client, technical_request["id"], "detalhes.txt", b"Conteudo detalhado do problema.")
    assert upload.status_code == 201

    detail = client.get(
        f"/api/v1/requests/{technical_request['id']}", headers=authenticated_csrf_headers(client)
    )
    assert detail.json()["status"] == "AWAITING_CONTEXT"


def test_other_user_cannot_see_or_upload_to_someone_elses_request(client: TestClient) -> None:
    register(client, OWNER)
    technical_request = create_qualified_request(client)
    _upload(client, technical_request["id"], "notas.txt", b"Conteudo de teste do anexo.")

    client.post("/api/v1/auth/logout", headers=authenticated_csrf_headers(client))
    register(client, OTHER_USER)

    upload_attempt = _upload(client, technical_request["id"], "intruso.txt", b"tentativa alheia")
    assert upload_attempt.status_code == 404

    list_attempt = client.get(
        f"/api/v1/requests/{technical_request['id']}/attachments",
        headers=authenticated_csrf_headers(client),
    )
    assert list_attempt.status_code == 404


def test_delete_attachment(client: TestClient) -> None:
    register(client, OWNER)
    technical_request = create_qualified_request(client)
    uploaded = _upload(client, technical_request["id"], "notas.txt", b"Conteudo de teste do anexo.").json()

    delete_response = client.delete(
        f"/api/v1/requests/{technical_request['id']}/attachments/{uploaded['id']}",
        headers=authenticated_csrf_headers(client),
    )
    assert delete_response.status_code == 204

    listed = client.get(
        f"/api/v1/requests/{technical_request['id']}/attachments",
        headers=authenticated_csrf_headers(client),
    )
    assert listed.json() == []


def test_delete_nonexistent_attachment_returns_404(client: TestClient) -> None:
    register(client, OWNER)
    technical_request = create_qualified_request(client)

    response = client.delete(
        f"/api/v1/requests/{technical_request['id']}/attachments/does-not-exist",
        headers=authenticated_csrf_headers(client),
    )
    assert response.status_code == 404
