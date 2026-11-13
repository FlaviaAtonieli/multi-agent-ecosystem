"""Repositório público do GitHub como base de conhecimento de um comitê.

Ao adicionar, a indexação roda em segundo plano: lê os metadados, baixa o código
compactado, lê os arquivos de texto em memória e grava os trechos com embeddings,
ligados ao comitê. Nada é gravado em disco nem executado.

Segurança: só github.com (a URL é validada e o download vai sempre ao endereço da
API configurado, então um link não aponta o servidor para outro lugar); caminhos do
pacote que saem da pasta são ignorados, assim como links simbólicos e binários. Os
limites de tamanho, de arquivos e de caracteres seguram memória e custo de embeddings.
"""

import asyncio
import io
import logging
import re
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath

import httpx
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.database import SessionLocal
from app.models import ClanRepository, KnowledgeChunk
from app.rag.cache import CachedEmbeddingProvider
from app.rag.factory import create_embedding_provider
from app.rag.ingestion import chunk_text
from app.services.artifact_service import safe_relative_path

logger = logging.getLogger(__name__)

_GITHUB_URL = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/(?P<name>[A-Za-z0-9._-]{1,100}?)(?:\.git)?/?$"
)
_EXTRA_EXTENSIONS = {".html", ".css", ".scss", ".toml", ".cfg", ".ini", ".gradle", ".properties", ".rst"}
_EXTRA_FILENAMES = {"dockerfile", "makefile", "readme", "license"}
_SKIPPED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "vendor",
    "venv",
    ".venv",
    "__pycache__",
    "target",
    "coverage",
    ".next",
    ".idea",
    ".vscode",
}
_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".kt": "kotlin",
    ".rs": "rust",
    ".sql": "sql",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
}
_EMBEDDING_BATCH = 64
_MAX_UNPACK_RATIO = 10
_INTERRUPTED = "A indexação parou porque o servidor reiniciou. Peça para indexar de novo."

_background_tasks: set[asyncio.Task] = set()


class InvalidRepositoryUrl(ValueError):
    pass


class RepositoryIndexingError(RuntimeError):
    """Falha que pode ser mostrada como está para quem adicionou o repositório."""


@dataclass(frozen=True)
class RepositoryFile:
    path: str
    content: str


def parse_github_url(url: str) -> tuple[str, str]:
    match = _GITHUB_URL.match(url.strip())
    if match is None or match["name"] in (".", ".."):
        raise InvalidRepositoryUrl(
            "Informe o endereço de um repositório público do GitHub, como https://github.com/dono/repositorio."
        )
    return match["owner"], match["name"]


def _allowed_file(path: str, config: Settings) -> bool:
    parts = PurePosixPath(path).parts
    if any(part in _SKIPPED_DIRS for part in parts[:-1]):
        return False
    filename = parts[-1].lower()
    suffix = PurePosixPath(filename).suffix
    if suffix in config.attachment_allowed_extension_list or suffix in _EXTRA_EXTENSIONS:
        return True
    return PurePosixPath(filename).stem in _EXTRA_FILENAMES and suffix in ("", ".txt")


def _github_get(url: str, *, config: Settings) -> httpx.Response:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "flavia-plataforma-de-agentes"}
    return httpx.get(url, headers=headers, timeout=20, follow_redirects=True)


def _metadata(owner: str, name: str, config: Settings) -> str:
    response = _github_get(f"{config.github_api_base_url}/repos/{owner}/{name}", config=config)
    if response.status_code == 404:
        raise RepositoryIndexingError(
            "O repositório não foi encontrado ou é privado. Só repositórios públicos são aceitos."
        )
    if response.status_code != 200:
        raise RepositoryIndexingError(
            f"O GitHub não respondeu como esperado (status {response.status_code})."
        )
    data = response.json()
    if data.get("private"):
        raise RepositoryIndexingError(
            "O repositório não foi encontrado ou é privado. Só repositórios públicos são aceitos."
        )
    size_mb = (data.get("size") or 0) / 1024
    if size_mb > config.repository_max_download_mb:
        raise RepositoryIndexingError(
            f"O repositório tem cerca de {size_mb:.0f} MB, maior que o limite de "
            f"{config.repository_max_download_mb} MB."
        )
    return str(data.get("default_branch") or "main")


def _download(owner: str, name: str, branch: str, config: Settings) -> bytes:
    limit = config.repository_max_download_mb * 1024 * 1024
    url = f"{config.github_api_base_url}/repos/{owner}/{name}/tarball/{branch}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "flavia-plataforma-de-agentes"}
    buffer = bytearray()
    with httpx.stream("GET", url, headers=headers, timeout=60, follow_redirects=True) as response:
        if response.status_code != 200:
            raise RepositoryIndexingError(
                f"Não foi possível baixar o código (status {response.status_code})."
            )
        for part in response.iter_bytes():
            buffer.extend(part)
            if len(buffer) > limit:
                raise RepositoryIndexingError(
                    f"O download passou de {config.repository_max_download_mb} MB e foi interrompido."
                )
    return bytes(buffer)


def read_text_files(archive: bytes, config: Settings) -> list[RepositoryFile]:
    """Arquivos de texto do pacote, sem a pasta raiz que o GitHub acrescenta."""
    files: list[RepositoryFile] = []
    total_chars = 0
    max_file_bytes = config.repository_max_file_kb * 1024
    # Pacote pequeno que descompacta para gigabytes: para de ler antes de gastar a CPU.
    max_unpacked = config.repository_max_download_mb * 1024 * 1024 * _MAX_UNPACK_RATIO
    unpacked = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            for member in tar:
                if len(files) >= config.repository_max_files:
                    break
                unpacked += max(member.size, 0)
                if unpacked > max_unpacked:
                    raise RepositoryIndexingError(
                        "O repositório descompactado passou do limite e a leitura foi interrompida."
                    )
                # Só arquivos comuns: links simbólicos e de disco nunca são seguidos.
                if not member.isfile() or member.size > max_file_bytes:
                    continue
                _, _, inside_root = member.name.partition("/")
                path = safe_relative_path(inside_root)
                if path is None or not _allowed_file(path, config):
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                raw = extracted.read()
                if b"\x00" in raw:
                    continue
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                if not text.strip():
                    continue
                if total_chars + len(text) > config.repository_max_total_chars:
                    break
                total_chars += len(text)
                files.append(RepositoryFile(path=path, content=text))
    except tarfile.TarError as exc:
        raise RepositoryIndexingError("O pacote baixado do GitHub não pôde ser lido.") from exc
    return files


def _store_chunks(
    db: Session, repository: ClanRepository, files: list[RepositoryFile], config: Settings
) -> int:
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.repository_id == repository.id))
    windows: list[tuple[RepositoryFile, int, tuple[str, int, int]]] = []
    for file in files:
        for index, window in enumerate(
            chunk_text(file.content, max_chars=config.rag_chunk_max_chars, overlap=config.rag_chunk_overlap)
        ):
            windows.append((file, index, window))

    provider = CachedEmbeddingProvider(create_embedding_provider(config), db, model=config.embedding_model)
    for start in range(0, len(windows), _EMBEDDING_BATCH):
        batch = windows[start : start + _EMBEDDING_BATCH]
        embeddings = provider.embed([window[2][0] for window in batch])
        for (file, index, (content, char_start, char_end)), embedding in zip(batch, embeddings, strict=True):
            db.add(
                KnowledgeChunk(
                    artifact_name=f"{repository.owner}/{repository.name}:{file.path}"[:200],
                    source_type="clan_repository",
                    language=_LANGUAGES.get(PurePosixPath(file.path).suffix.lower()),
                    content=content,
                    embedding=embedding,
                    chunk_index=index,
                    char_start=char_start,
                    char_end=char_end,
                    clan_id=repository.clan_id,
                    repository_id=repository.id,
                )
            )
    return len(windows)


def index_repository(repository_id: str, config: Settings = settings) -> None:
    with SessionLocal() as db:
        repository = db.get(ClanRepository, repository_id)
        if repository is None:
            return
        repository.status = "INDEXING"
        repository.error_message = None
        db.commit()
        try:
            branch = _metadata(repository.owner, repository.name, config)
            files = read_text_files(_download(repository.owner, repository.name, branch, config), config)
            if not files:
                raise RepositoryIndexingError(
                    "Nenhum arquivo de texto ou código foi encontrado no repositório."
                )
            repository.chunk_count = _store_chunks(db, repository, files, config)
            repository.file_count = len(files)
            repository.status = "READY"
            repository.indexed_at = datetime.now(UTC)
        except RepositoryIndexingError as exc:
            db.rollback()
            repository.status = "FAILED"
            repository.error_message = str(exc)
        except Exception as exc:  # noqa: BLE001 - ninguém espera a resposta: o erro fica no repositório
            db.rollback()
            logger.warning("Falha ao indexar o repositório %s: %s", repository_id, type(exc).__name__)
            repository.status = "FAILED"
            repository.error_message = "Não foi possível indexar o repositório. Tente de novo mais tarde."
        db.commit()


def start_indexing_in_background(repository_id: str) -> None:
    """A indexação baixa e lê o código e chama o modelo de embeddings: leva mais que uma
    requisição deve esperar. A tela acompanha pelo status do repositório."""
    task = asyncio.get_running_loop().create_task(asyncio.to_thread(index_repository, repository_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


def find_repository(db: Session, *, clan_id: str, owner: str, name: str) -> ClanRepository | None:
    return db.scalar(
        select(ClanRepository).where(
            ClanRepository.clan_id == clan_id,
            func.lower(ClanRepository.owner) == owner.lower(),
            func.lower(ClanRepository.name) == name.lower(),
        )
    )


def remove_repository(db: Session, repository: ClanRepository) -> None:
    # O SQLite dos testes não aplica ON DELETE CASCADE; o apagar explícito vale nos dois.
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.repository_id == repository.id))
    db.delete(repository)


def fail_interrupted_indexing(db: Session) -> int:
    """Chamado na subida, como a orquestração: a indexação vive só neste processo."""
    interrupted = list(
        db.scalars(select(ClanRepository).where(ClanRepository.status.in_(("PENDING", "INDEXING"))))
    )
    for repository in interrupted:
        repository.status = "FAILED"
        repository.error_message = _INTERRUPTED
    db.commit()
    return len(interrupted)
