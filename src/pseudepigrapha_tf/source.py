from __future__ import annotations

from pathlib import Path

from .model import Book
from .parser import EmptySourceError, parse_file


def load_source_directory(path: str | Path) -> tuple[list[Book], list[str]]:
    source_dir = Path(path)
    books: list[Book] = []
    warnings: list[str] = []
    for xml_path in sorted(source_dir.glob("*.xml")):
        if xml_path.name.startswith("."):
            continue
        try:
            books.append(parse_file(xml_path))
        except EmptySourceError:
            warnings.append(f"skipping empty XML source: {xml_path.name}")
    return books, warnings
