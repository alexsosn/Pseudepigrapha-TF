from __future__ import annotations

from collections import Counter, defaultdict, deque
from pathlib import Path
from xml.etree import ElementTree as ET

from . import audit_core as _core
from .parser import InvalidSourceError
from .source_versions import (
    GENERATED_TRANSLATION_MARKER,
    GeneratedTranslationClassificationError,
    is_generated_translation_version,
)

# Keep the pre-generated-layer audit implementation available as a stable core.
# Re-export its API, including private helpers used by semantic_audit.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


def _raw_translation_unit_identities(
    version: ET.Element,
    *,
    generated: bool,
) -> tuple[tuple[tuple[str, ...], str], ...]:
    """Reconstruct source identities directly from XML for audit-only mapping."""

    text = version.find("text")
    if text is None:
        return ()

    prefix = ""
    if generated:
        language = (version.get("language") or "").strip().lower()
        prefix = f"{language[:2]}_" if language else ""

    result: list[tuple[tuple[str, ...], str]] = []

    def walk(node: ET.Element, path: tuple[str, ...]) -> None:
        for child in node:
            tag = child.tag.lower()
            if tag in {"div", "chapter", "verse"}:
                number = (
                    child.get("number")
                    or child.get("reference")
                    or child.get("n")
                    or str(len(path) + 1)
                )
                walk(child, (*path, number))
            elif tag == "unit":
                unit_id = child.get("id", "")
                if generated and prefix and unit_id.startswith(prefix):
                    unit_id = unit_id[len(prefix) :]
                result.append((path, unit_id))

    walk(text, ())
    return tuple(result)


def _raw_generated_translation_evidence(
    source_dir: Path,
) -> tuple[list[dict], list[dict], dict[tuple[str, str, str, str, str], deque[str]]]:
    """Classify and map generated versions from raw XML, without parser-model reuse."""

    generated_records: list[dict] = []
    failures: list[dict] = []
    kind_queues: dict[tuple[str, str, str, str, str], deque[str]] = defaultdict(deque)

    for path in sorted(source_dir.glob("*.xml")):
        data = path.read_bytes()
        if path.name.startswith(".") or not data.strip():
            continue
        root = ET.fromstring(data)
        versions = root.findall("version")
        if not versions:
            key = (
                path.name,
                root.get("language", "") or "Default",
                root.get("language", ""),
                "",
                "",
            )
            kind_queues[key].append("source")
            continue

        classified: list[tuple[ET.Element, bool]] = []
        source_versions: list[ET.Element] = []
        for version in versions:
            try:
                generated = is_generated_translation_version(version)
            except GeneratedTranslationClassificationError as exc:
                raise InvalidSourceError(f"{path.name}: {exc}") from exc
            classified.append((version, generated))
            key = (
                path.name,
                version.get("title", ""),
                version.get("language", ""),
                version.get("author", ""),
                version.get("fragment", ""),
            )
            kind_queues[key].append("generated_translation" if generated else "source")
            if not generated:
                source_versions.append(version)

        source_signatures = [
            Counter(_raw_translation_unit_identities(version, generated=False))
            for version in source_versions
        ]
        for version, generated in classified:
            if not generated:
                continue
            identities = _raw_translation_unit_identities(version, generated=True)
            signature = Counter(identities)
            candidates = [
                source
                for source, source_signature in zip(source_versions, source_signatures)
                if source_signature == signature
            ]
            common = {
                "ocp_book": root.get("filename", ""),
                "version_title": version.get("title", ""),
                "language": version.get("language", ""),
                "source_file": path.name,
            }
            if len(candidates) != 1:
                failures.append({**common, "candidate_count": len(candidates)})
                continue
            source = candidates[0]
            generated_records.append(
                {
                    **common,
                    "marker": GENERATED_TRANSLATION_MARKER,
                    "source_version_title": source.get("title", ""),
                    "source_version_language": source.get("language", ""),
                    "unit_count": len(identities),
                    "aligned_unit_count": len(identities),
                }
            )

    return generated_records, failures, kind_queues


def _raw_inventory(source_dir: Path) -> dict:
    """Audit all XML versions while classifying the generated layer independently."""

    source_dir = Path(source_dir)
    generated_records, failures, kind_queues = _raw_generated_translation_evidence(source_dir)

    # audit_core predates generated-layer inclusion and skips OCP-Trans versions.
    # Its XML inventory logic remains useful if classification is disabled only
    # for this call. Structural classification has already been performed above.
    original_classifier = _core.is_generated_translation_version
    _core.is_generated_translation_version = lambda _version: False
    try:
        inventory = _core._raw_inventory(source_dir)
    finally:
        _core.is_generated_translation_version = original_classifier

    inventory["excluded_generated_translation_versions"] = []
    inventory["generated_translations"] = generated_records
    inventory["generated_translation_mapping_failures"] = failures

    for record in inventory["versions"]:
        key = (
            str(record["source_file"]),
            str(record["version_title"]),
            str(record["language"]),
            str(record["author"]),
            str(record["fragment"]),
        )
        queue = kind_queues.get(key)
        if not queue:
            raise InvalidSourceError(
                f"{record['source_file']}: audit could not classify version "
                f"{record['version_title']!r}"
            )
        record["version_kind"] = queue.popleft()

    leftovers = [key for key, queue in kind_queues.items() if queue]
    if leftovers:
        raise InvalidSourceError(f"audit version classification was not fully consumed: {leftovers!r}")

    return inventory


def _graph_inventory(data, node_index=None) -> dict:
    """Extend the core graph inventory with the explicit version kind."""

    inventory = _core._graph_inventory(data, node_index)
    for record, node in zip(
        inventory["versions"],
        _core._nodes(data, "book", node_index),
        strict=True,
    ):
        record["version_kind"] = _core._feature(data, "version_kind", node, "source")
    return inventory
