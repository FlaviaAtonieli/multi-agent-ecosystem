"""Arquivos que uma Agent Skill entrega junto com a resposta.

O modelo só gasta tokens para gerar o conteúdo. Depois de validados e guardados,
mostrar, baixar e compactar os arquivos não chama o modelo de novo.

Os nomes vêm do modelo, que pode ser influenciado pelo texto de uma solicitação ou
de um anexo, então nada neles é confiável: um "../" escaparia da pasta ao extrair o
ZIP. Os arquivos são sempre tratados como texto, e nada é executado.
"""

import io
import re
import unicodedata
import zipfile
from collections.abc import Iterable
from pathlib import PurePosixPath

from app.agent_catalog.contracts import ArquivoGerado

MAX_FILES_PER_RESPONSE = 20
MAX_FILE_BYTES = 500_000
MAX_TOTAL_BYTES = 2_000_000
MAX_PATH_LENGTH = 200

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
# Alguns modelos repetem o nome do campo do schema como pasta ("generated_files/GDD.md").
_SCHEMA_FIELD_FOLDER = "generated_files/"
_LOCAL_REFERENCE = re.compile(r"""(?:src|href)\s*=\s*["']([^"'#?]+)["']""", re.IGNORECASE)


def safe_relative_path(raw_name: str) -> str | None:
    """Devolve o caminho relativo normalizado, ou None se puder sair da pasta do projeto."""
    name = raw_name.strip().replace("\\", "/")
    if not name or len(name) > MAX_PATH_LENGTH or name.startswith("/") or _WINDOWS_DRIVE.match(name):
        return None
    if any(unicodedata.category(char) == "Cc" for char in name):
        return None

    parts = [part for part in name.split("/") if part not in ("", ".")]
    if not parts or ".." in parts or any(":" in part for part in parts):
        return None
    return "/".join(parts)


def _without_repeating(path: str, used: set[str]) -> str:
    candidate = path
    copy = 2
    while candidate in used:
        original = PurePosixPath(path)
        candidate = str(original.with_name(f"{original.stem} ({copy}){original.suffix}"))
        copy += 1
    used.add(candidate)
    return candidate


def prepare_files(files: Iterable[ArquivoGerado]) -> tuple[list[ArquivoGerado], list[str]]:
    """Separa o que pode ser guardado do que foi recusado. Um arquivo recusado não
    derruba a resposta da skill: os nomes recusados vão para a linha do tempo."""
    accepted: list[ArquivoGerado] = []
    rejected: list[str] = []
    used: set[str] = set()
    total_bytes = 0

    for file in files:
        raw_name = file.nome.strip()
        if raw_name.lower().startswith(_SCHEMA_FIELD_FOLDER) and len(raw_name) > len(_SCHEMA_FIELD_FOLDER):
            raw_name = raw_name[len(_SCHEMA_FIELD_FOLDER) :]
        path = safe_relative_path(raw_name)
        size = len(file.conteudo.encode("utf-8", errors="replace"))
        too_much = (
            len(accepted) >= MAX_FILES_PER_RESPONSE
            or size > MAX_FILE_BYTES
            or total_bytes + size > MAX_TOTAL_BYTES
        )
        # O caractere nulo indica conteúdo binário, e o PostgreSQL não o aceita em texto.
        if path is None or too_much or "\x00" in file.conteudo:
            rejected.append(file.nome[:MAX_PATH_LENGTH])
            continue
        accepted.append(ArquivoGerado(nome=_without_repeating(path, used), conteudo=file.conteudo))
        total_bytes += size

    return accepted, rejected


def check_package(files: Iterable[tuple[str, str]]) -> list[str]:
    """Confere, sem IA, se as páginas HTML de uma skill carregam arquivos que vieram junto.

    Recebe (caminho, conteúdo) dos arquivos de uma mesma skill, que ficam na mesma
    pasta do ZIP. Endereços externos, âncoras e data: não contam.
    """
    files = list(files)
    paths = {path for path, _ in files}
    issues: list[str] = []
    for path, content in files:
        if not path.lower().endswith((".html", ".htm")):
            continue
        base = PurePosixPath(path).parent
        for reference in _LOCAL_REFERENCE.findall(content):
            reference = reference.strip()
            if not reference or "://" in reference or reference.startswith(("//", "data:", "mailto:", "/")):
                continue
            target = safe_relative_path(str(base / reference))
            if target is not None and target not in paths:
                issues.append(f"{path} carrega {reference}, que não foi entregue.")
    return issues


def build_zip(files: Iterable[tuple[str, str, str]]) -> bytes:
    """Monta o ZIP a partir de (área, caminho, conteúdo), com uma pasta por área."""
    used: set[str] = set()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for domain, path, content in files:
            folder = safe_relative_path(domain.replace("/", "-")) or "skill"
            archive.writestr(_without_repeating(f"{folder}/{path}", used), content)
    return buffer.getvalue()
