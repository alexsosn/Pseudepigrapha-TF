from __future__ import annotations

import subprocess
from pathlib import Path

from .model import Book
from .parser import EmptySourceError, parse_bytes


def load_source_directory(path: str | Path) -> tuple[list[Book], list[str]]:
    source_dir = Path(path)
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
