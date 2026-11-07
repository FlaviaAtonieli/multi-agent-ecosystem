"""Detects when a request explicitly asks for files (script, código, README...).

Measured on 2026-11-05 with the free model dots-3-note and real knowledge-base
chunks: the model ignored a request for files in 2 of 13 attempts and answered
with analysis only. Knowing the request asks for files lets the Quality Gate
flag a response that came without them. The prompt also insists on them, with
no measured gain (8 of 8 with the old prompt and with the new one).

Only the fields that say what the person wants are checked (title, objective,
follow-up question). The problem description often mentions files that are
not being requested ("o arquivo de log mostra...").
"""

import re
import unicodedata

_FILE_WORDS = frozenset({"arquivo", "arquivos", "script", "scripts", "readme"})
_EXTENSIONS = frozenset(
    {
        "sql", "py", "java", "js", "ts", "tsx", "jsx", "md", "yml", "yaml", "json",
        "xml", "sh", "cs", "go", "kt", "txt", "csv", "html", "css",
    }
)
_VERBS = frozenset(
    {
        "gere", "gerar", "crie", "criar", "escreva", "escrever", "implemente",
        "implementar", "entregue", "entregar", "mande", "envie",
    }
)
_ARTIFACTS = frozenset(
    {
        "codigo", "classe", "classes", "funcao", "metodo", "teste", "testes", "projeto",
        "dockerfile", "pipeline", "migration", "migracao", "componente", "endpoint",
    }
)
_NEGATIONS = frozenset({"sem", "nao", "nenhum", "nenhuma"})
_NEGATION_WINDOW = 4
_ARTIFACT_WINDOW = 5


def _tokens(text: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9_\-]+(?:\.[a-z0-9]+)?", plain)


def _names_a_file(token: str) -> bool:
    if token in _FILE_WORDS:
        return True
    return "." in token and token.rsplit(".", 1)[1] in _EXTENSIONS


def _asks_to_write_code(tokens: list[str], index: int) -> bool:
    if tokens[index] not in _VERBS:
        return False
    following = tokens[index + 1 : index + 1 + _ARTIFACT_WINDOW]
    return any(token in _ARTIFACTS for token in following)


def asks_for_files(*texts: str | None) -> bool:
    tokens = _tokens(" . ".join(text for text in texts if text))
    for index, token in enumerate(tokens):
        if not (_names_a_file(token) or _asks_to_write_code(tokens, index)):
            continue
        before = tokens[max(0, index - _NEGATION_WINDOW) : index]
        if not _NEGATIONS.intersection(before):
            return True
    return False
