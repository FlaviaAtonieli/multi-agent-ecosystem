from app.models import RequestAttachment, TechnicalRequest
from app.services.llm_service import _build_safe_request


def _bare_technical_request(**overrides) -> TechnicalRequest:
    defaults = dict(
        id="req-1",
        trace_id="TRC-20260921-AAAAAA",
        title="Investigar lentidão no checkout",
        problem="O checkout está lento em horários de pico.",
        objective="Entender a causa raiz.",
        context="Contexto suficiente para qualificar a solicitação de teste.",
        restrictions=[],
    )
    defaults.update(overrides)
    return TechnicalRequest(**defaults)


def test_build_safe_request_has_no_attachments_context_when_none_attached() -> None:
    safe_request, *_ = _build_safe_request(_bare_technical_request())
    assert safe_request.attachments_context is None


def test_build_safe_request_includes_attachment_content_labeled_by_filename() -> None:
    technical_request = _bare_technical_request()
    technical_request.attachments = [
        RequestAttachment(
            id="att-1",
            technical_request_id=technical_request.id,
            uploaded_by_id="user-1",
            filename="regras_de_negocio.txt",
            content_type="text/plain",
            content="O desconto máximo permitido é 15% para clientes não-VIP.",
            size_bytes=10,
        )
    ]

    safe_request, *_ = _build_safe_request(technical_request)

    assert safe_request.attachments_context is not None
    assert "[Anexo: regras_de_negocio.txt]" in safe_request.attachments_context
    assert "desconto máximo permitido é 15%" in safe_request.attachments_context


def test_build_safe_request_concatenates_multiple_attachments() -> None:
    technical_request = _bare_technical_request()
    technical_request.attachments = [
        RequestAttachment(
            id="att-1",
            technical_request_id=technical_request.id,
            uploaded_by_id="user-1",
            filename="a.txt",
            content_type="text/plain",
            content="Conteúdo A.",
            size_bytes=1,
        ),
        RequestAttachment(
            id="att-2",
            technical_request_id=technical_request.id,
            uploaded_by_id="user-1",
            filename="b.txt",
            content_type="text/plain",
            content="Conteúdo B.",
            size_bytes=1,
        ),
    ]

    safe_request, *_ = _build_safe_request(technical_request)

    assert "[Anexo: a.txt]" in safe_request.attachments_context
    assert "[Anexo: b.txt]" in safe_request.attachments_context
    assert safe_request.attachments_context.index("a.txt") < safe_request.attachments_context.index(
        "b.txt"
    )
