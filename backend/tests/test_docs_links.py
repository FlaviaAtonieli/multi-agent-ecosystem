"""Link relativo quebrado na documentação faz o teste falhar."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# O histórico registra como o projeto era na época, inclusive arquivos que saíram depois.
SKIPPED = {"CHANGELOG.md"}


def _documents() -> list[Path]:
    documents = [path for path in ROOT.glob("*.md") if path.name not in SKIPPED]
    return documents + list((ROOT / "docs").rglob("*.md"))


def test_relative_links_point_to_existing_files() -> None:
    broken = []
    for document in _documents():
        for target in LINK.findall(document.read_text(encoding="utf-8")):
            if re.match(r"[a-z]+:", target) or target.startswith("#"):
                continue
            path = target.split("#", 1)[0]
            if path and not (document.parent / path).exists():
                broken.append(f"{document.relative_to(ROOT)} -> {target}")

    assert broken == []
