from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.models import LLMInvocation, TechnicalRequest
from tests.conftest import create_qualified_request, register
from tests.test_metrics import _metric_value

USER = {
    "name": "Usuaria LLM",
    "email": "usuaria.llm@example.com",
    "password": "StrongPassword!123",
}
LABELS = {"provider": "openrouter", "model": "openai/gpt-5-mini"}


def _record_invocation(
    technical_request: TechnicalRequest,
    index: int,
    *,
    status: str,
    latency_ms: int | None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> LLMInvocation:
    return LLMInvocation(
        technical_request_id=technical_request.id,
        user_id=technical_request.owner_id,
        trace_id=technical_request.trace_id,
        llm_call_id=f"chamada-{index}",
        provider=LABELS["provider"],
        model=LABELS["model"],
        purpose="TECHNICAL_PLANNING",
        prompt_template_id="technical-planner",
        prompt_template_version="v1",
        input_hash="a" * 64,
        status=status,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def test_llm_metrics_come_from_recorded_invocations(client: TestClient) -> None:
    """Rows written by a skill process must show up here, in the main process."""
    register(client, USER)
    created = create_qualified_request(client)

    with SessionLocal() as db:
        row = db.get(TechnicalRequest, created["id"])
        db.add_all(
            [
                _record_invocation(
                    row, 1, status="COMPLETED", latency_ms=1_500, input_tokens=100, output_tokens=40
                ),
                _record_invocation(
                    row, 2, status="COMPLETED", latency_ms=25_000, input_tokens=200, output_tokens=60
                ),
                _record_invocation(row, 3, status="FAILED", latency_ms=500),
                # Still running: not a finished call yet, so it must not be counted.
                _record_invocation(row, 4, status="STARTED", latency_ms=None),
            ]
        )
        db.commit()

    text = client.get("/metrics").text

    assert _metric_value(text, "agenthub_llm_invocations_total", **LABELS, status="COMPLETED") == 2
    assert _metric_value(text, "agenthub_llm_invocations_total", **LABELS, status="FAILED") == 1
    assert _metric_value(text, "agenthub_llm_invocations_total", **LABELS, status="STARTED") == 0
    assert _metric_value(text, "agenthub_llm_tokens_total", **LABELS, direction="input") == 300
    assert _metric_value(text, "agenthub_llm_tokens_total", **LABELS, direction="output") == 100

    bucket = "agenthub_llm_invocation_duration_seconds_bucket"
    assert _metric_value(text, bucket, **LABELS, le="0.5") == 1
    assert _metric_value(text, bucket, **LABELS, le="2.0") == 2
    assert _metric_value(text, bucket, **LABELS, le="30.0") == 3
    assert _metric_value(text, bucket, **LABELS, le="+Inf") == 3
    assert _metric_value(text, "agenthub_llm_invocation_duration_seconds_count", **LABELS) == 3
    assert _metric_value(text, "agenthub_llm_invocation_duration_seconds_sum", **LABELS) == 27.0


def test_metrics_stay_valid_without_llm_invocations(client: TestClient) -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "agenthub_llm_invocations_total{" not in response.text
