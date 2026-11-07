"""Entregas de umas skills como entrada das que escrevem código.

No cenário da batalha naval (06/11/2026), as skills rodavam ao mesmo tempo e o
código foi escrito sem ver o ACESSIBILIDADE.md nem o PLANO_DE_TESTES.md, que já
apontavam os três defeitos encontrados depois. Quando a solicitação pede
arquivos, as skills que escrevem código passam a rodar depois das outras e
recebem o que elas entregaram.

A primeira versão mandava os documentos inteiros (~6 mil caracteres) e o modelo
gratuito piorou: devolveu plano em vez de código, código quebrado ou nada. Agora
vão só as linhas de requisito (listas, itens numerados e "Esperado:"), sem código
de outros agentes, em até 2.500 caracteres.
"""

import re

# Extensões de código-fonte. Documentos (.md, .txt) e dados (.csv, .json) não contam:
# quem entrega só isso orienta, não implementa.
_CODE_EXTENSIONS = (
    "html", "htm", "css", "js", "jsx", "ts", "tsx", "py", "java", "kt", "cs", "go",
    "rb", "php", "swift", "c", "cpp", "h", "sql", "sh", "vue",
)
_CODE_FILE = re.compile(r"\.(" + "|".join(_CODE_EXTENSIONS) + r")\b", re.IGNORECASE)

DEFAULT_MAX_CHARS = 2500

TeamEntry = tuple[str, str, list[tuple[str, str]]]

_REQUIREMENT_LINE = re.compile(r"^\s*(?:[-*+]|\d+[.)]|esperado\b|crit[eé]rio\b)", re.IGNORECASE)
_LIST_MARKER = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s*")
_MARKDOWN = re.compile(r"[*_`#>]+")


def is_code_file(filename: str) -> bool:
    return filename.lower().rsplit(".", 1)[-1] in _CODE_EXTENSIONS if "." in filename else False


def writes_code(manifest: dict) -> bool:
    """Se a skill declara entregar arquivos de código em produced_outputs."""
    outputs = manifest.get("produced_outputs") or []
    return any(_CODE_FILE.search(str(output)) for output in outputs)


def _requirements(content: str) -> list[str]:
    lines: list[str] = []
    for raw in content.splitlines():
        if not _REQUIREMENT_LINE.match(raw):
            continue
        line = _MARKDOWN.sub("", _LIST_MARKER.sub("", raw)).strip()
        if len(line) > 3 and line not in lines:
            lines.append(line)
    return lines


def build_team_context(entries: list[TeamEntry], *, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """Resumo de cada skill e as linhas de requisito dos documentos dela, até max_chars.

    O espaço é dividido igualmente entre as skills, para um plano de testes longo
    não esconder as recomendações de acessibilidade.
    """
    if not entries:
        return ""
    per_entry = max(200, max_chars // len(entries))
    parts: list[str] = []
    for name, summary, files in entries:
        block = f"[{name}] {summary.strip()}"
        for filename, content in files:
            if is_code_file(filename):
                continue
            for line in _requirements(content):
                candidate = f"{block}\n- {line}"
                if len(candidate) > per_entry:
                    break
                block = candidate
        parts.append(block[:per_entry])
    return "\n\n".join(parts)[:max_chars]
