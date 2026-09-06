from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .model import Book, DocumentMetadata, DocumentMetadataCatalog, JsonScalar
from .parser import EmptySourceError, parse_bytes

INTRO_FIELDS = (
    "introduction",
    "provenance",
    "themes",
    "status",
    "manuscripts",
    "bibliography",
    "corrections",
    "sigla",
    "copyright",
)


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


def _object_without_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key in intros.json: {key!r}")
        result[key] = value
    return result


def _json_scalar(value: object, context: str) -> JsonScalar:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"{context} must be a JSON scalar")


def load_document_metadata(path: str | Path) -> DocumentMetadataCatalog:
    """Load committed public OCP ``intros.json`` without normalizing source strings.

    The exporter deliberately omits empty database fields, so field presence is
    preserved exactly. An explicit empty JSON string, if one is ever committed,
    remains distinct from a missing field.
    """

    source_dir = Path(path)
    intros_path = source_dir / "intros.json"
    if not intros_path.is_file():
        return DocumentMetadataCatalog(meta=(), documents=())

    try:
        payload = json.loads(
            intros_path.read_text(encoding="utf-8"),
            object_pairs_hook=_object_without_duplicate_keys,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"cannot parse {intros_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("intros.json root must be an object")
    unknown_top = set(payload) - {"_meta", "documents"}
    if unknown_top:
        raise ValueError(f"unknown intros.json top-level keys: {sorted(unknown_top)!r}")

    meta_obj = payload.get("_meta", {})
    documents_obj = payload.get("documents", {})
    if not isinstance(meta_obj, dict):
        raise ValueError("intros.json _meta must be an object")
    if not isinstance(documents_obj, dict):
        raise ValueError("intros.json documents must be an object")

    meta = tuple(
        (key, _json_scalar(value, f"intros.json _meta/{key}"))
        for key, value in meta_obj.items()
    )
    allowed_fields = frozenset(INTRO_FIELDS)
    xml_paths = {
        xml_path.name: xml_path
        for xml_path in source_dir.glob("*.xml")
        if not xml_path.name.startswith(".")
    }
    documents: list[DocumentMetadata] = []

    for source_file, entry in documents_obj.items():
        if not isinstance(source_file, str) or Path(source_file).name != source_file or not source_file.endswith(".xml"):
            raise ValueError(f"invalid intro document filename: {source_file!r}")
        xml_path = xml_paths.get(source_file)
        if xml_path is None:
            raise ValueError(f"{source_file}: intro document has no sibling XML")
        if not isinstance(entry, dict):
            raise ValueError(f"{source_file}: intro document entry must be an object")
        unknown_entry = set(entry) - {"title", "version", "fields", "citation"}
        if unknown_entry:
            raise ValueError(f"{source_file}: unknown intro entry keys: {sorted(unknown_entry)!r}")
        if "title" not in entry or not isinstance(entry["title"], str):
            raise ValueError(f"{source_file}: intro title must be a string")
        if "version" not in entry:
            raise ValueError(f"{source_file}: intro version is required")
        version = _json_scalar(entry["version"], f"{source_file}: intro version")
        fields_obj = entry.get("fields", {})
        if not isinstance(fields_obj, dict):
            raise ValueError(f"{source_file}: intro fields must be an object")
        unknown_fields = set(fields_obj) - allowed_fields
        if unknown_fields:
            raise ValueError(f"{source_file}: unknown intro field(s): {sorted(unknown_fields)!r}")

        fields: list[tuple[str, str]] = []
        for field_name, value in fields_obj.items():
            if not isinstance(value, str):
                raise ValueError(f"{source_file}: intro field {field_name!r} must be a string")
            fields.append((field_name, value))

        citation = entry.get("citation")
        if citation is not None and not isinstance(citation, str):
            raise ValueError(f"{source_file}: intro citation must be a string")

        xml_empty = not xml_path.read_bytes().strip()
        documents.append(
            DocumentMetadata(
                source_file=source_file,
                title=entry["title"],
                version=version,
                fields=tuple(fields),
                citation=citation,
                xml_empty=xml_empty,
            )
        )

    return DocumentMetadataCatalog(meta=meta, documents=tuple(documents))


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
