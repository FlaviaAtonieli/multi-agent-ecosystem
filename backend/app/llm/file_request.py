"""Detecta quando a solicitação pede arquivos (script, código, README...).

Medido com um modelo gratuito: ele ignorou o pedido de arquivos em 2 de 13
tentativas e respondeu só com análise. Sabendo do pedido, o Quality Gate aponta a
resposta que veio sem eles; insistir no prompt não mostrou ganho medido.

Só os campos que dizem o que a pessoa quer são lidos (título, objetivo, pergunta de
acompanhamento): a descrição do problema cita arquivos que não estão sendo pedidos
("o arquivo de log mostra...").
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
