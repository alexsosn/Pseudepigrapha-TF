from __future__ import annotations

import subprocess
from pathlib import Path

from .model import Book
from .parser import EmptySourceError, parse_bytes


_REVIEWED_NON_CORPUS_FILES = frozenset({
    ".TJob.xml.un~",
    "grammateus.dtd",
    "tags",
})
_REVIEWED_NON_CORPUS_DIRECTORIES = frozenset({"backups", "drafts"})
_SUPPORTED_METADATA_FILES = frozenset({"intros.json"})


def validate_source_boundary(path: str | Path) -> None:
    """Fail when an OCP docs directory contains unreviewed source material.

    The converter intentionally consumes only published root-level ``*.xml``
    documents plus the public ``intros.json`` export.  The pinned upstream tree
    also contains explicitly reviewed editor/schema artifacts and historical
    working-copy directories.  Anything else must be reviewed before a source
    refresh can silently widen (or change) the scholarly input boundary.
    """

    source_dir = Path(path)
    unexpected: list[str] = []
    for entry in sorted(source_dir.iterdir(), key=lambda item: item.name):
        name = entry.name
        if entry.is_symlink():
            unexpected.append(name)
        elif entry.is_dir():
            if name not in _REVIEWED_NON_CORPUS_DIRECTORIES:
                unexpected.append(f"{name}/")
        elif entry.is_file():
            if name in _SUPPORTED_METADATA_FILES or name in _REVIEWED_NON_CORPUS_FILES:
                continue
            if name.endswith(".xml") and not name.startswith("."):
                continue
            unexpected.append(name)
        else:
            unexpected.append(name)

    if unexpected:
        raise ValueError(
            "unreviewed OCP source material in "
            f"{source_dir}: {', '.join(unexpected)}"
        )


def load_source_directory(path: str | Path) -> tuple[list[Book], list[str]]:
    source_dir = Path(path)
    validate_source_boundary(source_dir)
    books: list[Book] = []
    warnings: list[str] = []
    for xml_path in sorted(source_dir.glob("*.xml")):
        if xml_path.name.startswith("."):
            continue
        try:
            book = parse_bytes(xml_path.read_bytes(), source_path=xml_path.name)
        except EmptySourceError:
            warnings.append(f"skipping empty XML source: {xml_path.name}")
            continue
        for exclusion in book.excluded_generated_translations:
            warnings.append(
                "excluding generated translation "
                f"{book.filename}/{exclusion.version_title} ({exclusion.language}); "
                f"source marker={exclusion.marker}"
            )
        books.append(book)
    return books, warnings


def detect_git_commit(path: str | Path) -> str:
    """Return the Git commit containing *path*, or an empty string outside a Git checkout."""
    try:
        result = subprocess.run(
            ["git", "-C", str(Path(path)), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip()


def git_source_is_clean(path: str | Path) -> bool:
    """Return whether the supplied source directory exactly reflects Git HEAD.

    Verification is deliberately conservative: any tracked, untracked, or
    ignored filesystem change below the supplied directory makes the source
    unsuitable for an exact pinned-source license assertion. Conversion may
    still proceed; callers can downgrade provenance to unverified.
    """

    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(Path(path)),
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                "--ignored=matching",
                "--",
                ".",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    return not result.stdout.strip()
