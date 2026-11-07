"""Entregas de umas skills como entrada das que escrevem código.

No cenário da batalha naval (06/11/2026), as skills rodavam ao mesmo tempo e o
código foi escrito sem ver o ACESSIBILIDADE.md nem o PLANO_DE_TESTES.md, que já
apontavam os três defeitos encontrados depois. Quando a solicitação pede
arquivos, as skills que escrevem código passam a rodar depois das outras e
recebem o que elas entregaram. O número de chamadas ao modelo não muda.
"""

import re

# Extensões de código-fonte. Documentos (.md, .txt) e dados (.csv, .json) não contam:
# quem entrega só isso orienta, não implementa.
_CODE_EXTENSIONS = (
    "html", "htm", "css", "js", "jsx", "ts", "tsx", "py", "java", "kt", "cs", "go",
    "rb", "php", "swift", "c", "cpp", "h", "sql", "sh", "vue",
)
_CODE_FILE = re.compile(r"\.(" + "|".join(_CODE_EXTENSIONS) + r")\b", re.IGNORECASE)

DEFAULT_MAX_CHARS = 6000

TeamEntry = tuple[str, str, list[tuple[str, str]]]


def writes_code(manifest: dict) -> bool:
    """Se a skill declara entregar arquivos de código em produced_outputs."""
    outputs = manifest.get("produced_outputs") or []
    return any(_CODE_FILE.search(str(output)) for output in outputs)


def build_team_context(entries: list[TeamEntry], *, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Texto com o resumo e os documentos de cada skill, dentro de max_chars.

    O espaço é dividido igualmente entre os documentos, para um plano de testes
    longo não esconder as recomendações de acessibilidade.
    """
    documents = sum(len(files) for _, _, files in entries) or 1
    headers = sum(len(name) + len(summary) + 40 for name, summary, _ in entries)
    per_document = max(300, (max_chars - headers) // documents)

    parts: list[str] = []
    for name, summary, files in entries:
        parts.append(f"[{name}] {summary}")
        for filename, content in files:
            text = content.strip()
            if len(text) > per_document:
                text = text[:per_document].rstrip() + " [...]"
            parts.append(f"--- {filename} ---\n{text}")
    return "\n\n".join(parts)[:max_chars]
