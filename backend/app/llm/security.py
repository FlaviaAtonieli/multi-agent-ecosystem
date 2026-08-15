import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SanitizedContent:
    value: str
    redacted_fields_count: int
    truncated: bool


_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(?i)\b(bearer)\s+[a-z0-9._~+\-/]+=*"),
        r"\1 [REDACTED]",
    ),
    (
        # Covers sk-... key formats from OpenAI, OpenRouter (sk-or-v1-...) and similar providers.
        re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
        "[REDACTED_API_KEY]",
    ),
    (
        re.compile(
            r"(?i)\b(password|passwd|senha|secret|api[_-]?key|token|session[_-]?id)\b\s*[:=]\s*([^\s,;]+)"
        ),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
)


def content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def sanitize_content(content: str, *, max_chars: int, redact: bool) -> SanitizedContent:
    value = content
    redactions = 0

    if redact:
        for pattern, replacement in _PATTERNS:
            value, count = pattern.subn(replacement, value)
            redactions += count

    truncated = len(value) > max_chars
    if truncated:
        value = value[:max_chars]

    return SanitizedContent(
        value=value,
        redacted_fields_count=redactions,
        truncated=truncated,
    )
