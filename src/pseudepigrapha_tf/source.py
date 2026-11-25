from __future__ import annotations

import subprocess
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree as ET

from .model import Book
from .parser import EmptySourceError, InvalidSourceError, parse_bytes


_REVIEWED_NON_CORPUS_FILES = frozenset({
    ".TJob.xml.un~",
    "grammateus.dtd",
    "tags",
})
_REVIEWED_NON_CORPUS_DIRECTORIES = frozenset({"backups", "drafts"})
_SUPPORTED_METADATA_FILES = frozenset({"intros.json"})


_TEI = "{http://www.tei-c.org/ns/1.0}"
_MORPHOLOGY_FILE = "ApDan_TEI.xml"


def is_separate_morphology(path: Path) -> bool:
    """Recognize the reviewed extra ApDan annotation, never by name alone."""
    if path.name != _MORPHOLOGY_FILE:
        return False
    from .apdan_morphology import CANDIDATE_MORPH_BLOB, _git_blob_sha

    base = path.with_name("ApDan.xml")
    if (path.is_symlink() or not path.is_file() or base.is_symlink()
            or not base.is_file() or not base.stat().st_size
            or _git_blob_sha(path.read_bytes()) != CANDIDATE_MORPH_BLOB):
        raise ValueError(f"{path.name}: unreviewed separate ApDan morphology source")
    return True


def excluded_source_layers(source_dir: Path) -> list[dict[str, str]]:
    """Inventory known non-independent XML layers from the actual source tree."""
    excluded: list[dict[str, str]] = []
    morphology = source_dir / _MORPHOLOGY_FILE
    if morphology.exists() or morphology.is_symlink():
        if is_separate_morphology(morphology):
            excluded.append({"path": morphology.name, "kind": "separate_morphology",
                             "sha256": sha256(morphology.read_bytes()).hexdigest()})
    mirrors = source_dir / "tei"
    if mirrors.exists() or mirrors.is_symlink():
        if mirrors.is_symlink() or not mirrors.is_dir():
            raise ValueError("tei/: expected a regular directory of derived mirrors")
        for mirror in sorted(mirrors.iterdir()):
            label = f"tei/{mirror.name}"
            original = source_dir / mirror.name
            if (mirror.is_symlink() or not mirror.is_file()
                    or mirror.suffix != ".xml" or mirror.name.startswith(".")
                    or mirror.name == _MORPHOLOGY_FILE
                    or original.is_symlink() or not original.is_file()
                    or not original.stat().st_size):
                raise ValueError(f"{label}: unreviewed TEI material or missing root source")
            payload = mirror.read_bytes()
            try:
                root = ET.fromstring(payload)
            except ET.ParseError as exc:
                raise ValueError(f"{label}: invalid TEI mirror") from exc
            responses = {
                "".join(node.itertext()).strip()
                for node in root.findall(
                    f"{_TEI}teiHeader/{_TEI}fileDesc/{_TEI}titleStmt/"
                    f"{_TEI}respStmt/{_TEI}resp"
                )
            }
            if (root.tag != _TEI + "TEI"
                    or "TEI P5 conversion from OCP Grammateus XML" not in responses):
                raise ValueError(f"{label}: unreviewed TEI mirror declaration")
            excluded.append({"path": label, "kind": "derived_tei_mirror",
                             "sha256": sha256(payload).hexdigest()})
    return excluded


def validate_source_boundary(path: str | Path) -> list[dict[str, str]]:
    """Fail when an OCP docs directory contains unreviewed source material.

    The converter intentionally consumes only published root-level ``*.xml``
    textual documents plus the public ``intros.json`` export. Derived TEI mirrors
    and the reviewed separate ApDan morphology are inventoried, not interpreted
    as independent editions. The returned list describes these exclusions.
    The pinned upstream tree
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
            if name not in _REVIEWED_NON_CORPUS_DIRECTORIES and name != "tei":
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
    return excluded_source_layers(source_dir)


def load_source_directory(path: str | Path) -> tuple[list[Book], list[str]]:
    source_dir = Path(path)
    excluded = validate_source_boundary(source_dir)
    excluded_roots = {item["path"] for item in excluded}
    books: list[Book] = []
    warnings = [f'excluding {item["kind"]}: {item["path"]}' for item in excluded]
    work_sources: dict[str, str] = {}
    for xml_path in sorted(source_dir.glob("*.xml")):
        if xml_path.name.startswith(".") or xml_path.name in excluded_roots:
            continue
        try:
            book = parse_bytes(xml_path.read_bytes(), source_path=xml_path.name)
        except EmptySourceError:
            warnings.append(f"skipping empty XML source: {xml_path.name}")
            continue
        # Distinct source files claiming one OCP work identity cannot be
        # exposed as separate TF books with the same researcher-facing key.
        # Keep exact source spelling; never merge or normalize editorial IDs.
        earlier = work_sources.get(book.filename)
        if earlier is not None:
            raise InvalidSourceError(
                f"duplicate OCP book filename {book.filename!r} in "
                f"{earlier} and {xml_path.name}"
            )
        if book.filename != xml_path.stem:
            raise InvalidSourceError(
                f"{xml_path.name}: OCP <book filename> identity {book.filename!r} "
                f"does not match XML filename stem {xml_path.stem!r}"
            )
        work_sources[book.filename] = xml_path.name
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
    unsuitable for an exact pinned-source license assertion. Git's porcelain
    status can *hide* changes to index entries marked assume-unchanged or
    skip-worktree, so those index hints also forbid attestation. Conversion
    may still proceed; callers can downgrade provenance to unverified.
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
    if result.stdout.strip():
        return False

    # Porcelain status is not an identity proof for assume-unchanged or
    # skip-worktree index entries: both can conceal modified working files.
    # "git ls-files -v" marks ordinary tracked files with "H ", hidden
    # assume-unchanged files with lowercase "h ", and skip-worktree with
    # "S ". Reject any non-ordinary tag rather than guessing source bytes.
    try:
        tracked = subprocess.run(
            ["git", "-C", str(Path(path)), "ls-files", "-v", "--", "."],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    entries = tracked.stdout.splitlines()
    return bool(entries) and all(entry.startswith("H ") for entry in entries)
