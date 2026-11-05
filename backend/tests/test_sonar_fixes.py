import time

import pytest
from fastapi.testclient import TestClient

from app.agent_manifest.manifest import (
    _extract_bullets,
    _extract_identification_fields,
    _split_sections,
)
from app.core.config import settings

# Os textos são longos o bastante para uma expressão regular de tempo quadrático
# levar dezenas de segundos, e o limite é folgado para não falhar em CI lento.
LONG = 100_000
TIME_LIMIT_SECONDS = 1.0


@pytest.mark.parametrize(
    "parse",
    [
        lambda: _split_sections("## a" + " " * LONG + "b"),
        lambda: _split_sections("# a" + " " * LONG + "b"),
        lambda: _extract_bullets("- a" + " " * LONG + "b"),
        lambda: _extract_identification_fields("-" + " " * LONG + "a"),
    ],
)
def test_manifest_parsing_is_not_slowed_by_long_whitespace(parse) -> None:
    started = time.perf_counter()
    parse()
    assert time.perf_counter() - started < TIME_LIMIT_SECONDS


def test_section_parsing_keeps_title_and_sections() -> None:
    title, sections = _split_sections("# Skill de Teste  \n\n## Objetivo  \nAvaliar.\n\n## Limites\n- Um\n")

    assert title == "Skill de Teste"
    assert sections == {"Objetivo": "Avaliar.", "Limites": "- Um"}


def test_section_header_needs_text_on_the_same_line() -> None:
    _, sections = _split_sections("##\nNão é seção\n\n## Objetivo\nAvaliar.")

    assert sections == {"Objetivo": "Avaliar."}


def test_bullets_and_fields_keep_their_values() -> None:
    assert _extract_bullets("-   Primeiro  \n- Segundo\nsem marcador") == ["Primeiro", "Segundo"]
    assert _extract_identification_fields("- Nome:  Skill  \n-Versão: 1.0\n- URL: https://a.b/c") == {
        "nome": "Skill",
        "versao": "1.0",
        "url": "https://a.b/c",
    }


def test_error_from_size_limit_keeps_cors_headers(client: TestClient) -> None:
    """O CORS precisa ser o middleware mais externo: sem os cabeçalhos, o navegador
    esconde a resposta de erro, e a tela não consegue mostrar o motivo."""
    origin = settings.cors_origin_list[0]

    response = client.post(
        "/api/v1/auth/login",
        content=b"x",
        headers={
            "Origin": origin,
            "Content-Length": str(settings.max_request_body_bytes + 1),
        },
    )

    assert response.status_code == 413
    assert response.headers.get("access-control-allow-origin") == origin
