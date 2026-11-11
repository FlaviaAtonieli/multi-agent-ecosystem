"""Primeira camada da validação de contexto: regras fixas, sem IA e sem custo.

Só o tamanho mínimo deixava passar "TESTE TESTE TESTE..." e textos parecidos,
que gastariam uma orquestração inteira sem nada para analisar. Estas regras
barram o que claramente não descreve um cenário. Não julgam se o contexto é
bom o bastante: isso é papel do Orientador, que só sugere e nunca bloqueia.
"""

import re
import unicodedata

CONTEXT_MIN_LENGTH = 40
MIN_CONTENT_WORDS = 5
# Problema e objetivo podem ser curtos ("O job demora."), mas não vazios de sentido.
MIN_DESCRIPTION_WORDS = 2
# Abaixo disso, a maior parte das sequências de três palavras se repete.
MIN_DISTINCT_TRIGRAM_RATIO = 0.5
_MIN_TOKENS_FOR_REPETITION = 12

# Palavras de preenchimento contam juntas como uma só, então "teste" ainda
# vale numa frase real ("teste de integração do pagamento falhando").
_FILLER = frozenset(
    {
        "teste", "testes", "test", "tests", "testing", "testando", "testar",
        "lorem", "ipsum", "dolor", "sit", "amet",
        "asdf", "qwerty", "abc", "xyz", "xxx", "foo", "bar", "baz",
        "bla", "blabla", "blah", "ok", "oi", "ola", "hello", "hi",
    }
)

_STOPWORDS = frozenset(
    {
        "o", "a", "os", "as", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das",
        "em", "no", "na", "nos", "nas", "por", "para", "com", "sem", "e", "ou", "que",
        "se", "ao", "aos", "mas", "cada", "the", "of", "and", "to", "in", "on", "for",
        "with", "is", "it", "this", "that", "be",
    }
)

_KEYBOARD_RUNS = (
    "asdf", "sdfg", "dfgh", "fghj", "ghjk", "hjkl", "qwer", "rtyu", "tyui", "yuio",
    "uiop", "zxcv", "xcvb", "cvbn", "vbnm",
)

ISSUE_TOO_SHORT = f"Escreva pelo menos {CONTEXT_MIN_LENGTH} caracteres de contexto."
ISSUE_FEW_WORDS = (
    "Use mais palavras que descrevam o cenário: tecnologias, módulos, o que acontece e o que se espera."
)
ISSUE_REPETITIVE = "O texto se repete. Troque as repetições por detalhes do cenário."


def _tokens(text: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", plain)


def _is_noise(token: str) -> bool:
    if token.isdigit():
        return True
    if len(token) >= 4 and re.fullmatch(r"(.+?)\1+", token):
        return True  # kkkk, hahaha, asdfasdf
    return any(run in token for run in _KEYBOARD_RUNS)


def _content_word_count(tokens: list[str]) -> int:
    words = set()
    for token in tokens:
        if token in _STOPWORDS or _is_noise(token):
            continue
        words.add("<preenchimento>" if token in _FILLER else token)
    return len(words)


def _is_repetitive(tokens: list[str]) -> bool:
    if len(tokens) < _MIN_TOKENS_FOR_REPETITION:
        return False
    trigrams = list(zip(tokens, tokens[1:], tokens[2:], strict=False))
    return len(set(trigrams)) / len(trigrams) < MIN_DISTINCT_TRIGRAM_RATIO


def describes_something(text: str | None) -> bool:
    """Regra mais leve, para problema e objetivo: ao menos 2 palavras com conteúdo e sem repetição."""
    tokens = _tokens(text or "")
    return _content_word_count(tokens) >= MIN_DESCRIPTION_WORDS and not _is_repetitive(tokens)


def context_issues(context: str | None) -> list[str]:
    """O que impede o contexto de qualificar a solicitação; vazio quando passa."""
    text = (context or "").strip()
    tokens = _tokens(text)
    issues = []
    if len(text) < CONTEXT_MIN_LENGTH:
        issues.append(ISSUE_TOO_SHORT)
    if _content_word_count(tokens) < MIN_CONTENT_WORDS:
        issues.append(ISSUE_FEW_WORDS)
    if _is_repetitive(tokens):
        issues.append(ISSUE_REPETITIVE)
    return issues
