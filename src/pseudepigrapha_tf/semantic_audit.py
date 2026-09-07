from __future__ import annotations

from pathlib import Path

from . import audit
from . import semantic_audit_core as _core
from .graph import TFData
from .model import Book

for _name in dir(_core):
    if not _name.startswith("__") and _name not in {"build_conversion_report", "write_conversion_report"}:
        globals()[_name] = getattr(_core, _name)

_BASE_METADATA_VERSION_INVENTORY = _core._metadata_version_inventory


def _metadata_version_inventory_with_kind(data: TFData, node_index: dict[str, list[int]] | None = None) -> tuple[list[dict], list[dict]]:
    versions, specs = _BASE_METADATA_VERSION_INVENTORY(data, node_index)
    nodes = audit._nodes(data, "version_metadata", node_index)
    if len(versions) != len(nodes):
        raise ValueError(
            "semantic audit metadata inventory order mismatch: "
            f"{len(versions)} records for {len(nodes)} version_metadata nodes"
        )
    for record, node in zip(versions, nodes, strict=True):
        record["version_kind"] = audit._feature(data, "version_kind", node, "source")
    return versions, specs


def _graph_generated_translation_inventory(data: TFData, node_index: dict[str, list[int]]) -> list[dict]:
    """Project generated/source alignment independently from graph provenance."""

    version_kind = data.node_features.get("version_kind", {})
    version_id = data.node_features.get("version_id", {})
    translation_of = data.edge_features.get("translation_of", {})
    translation_unit_of = data.edge_features.get("translation_unit_of", {})
    units_by_version: dict[str, list[int]] = {}
    for unit in node_index.get("unit", []):
        units_by_version.setdefault(str(version_id.get(unit, "")), []).append(unit)

    records: list[dict] = []
    for book in node_index.get("book", []):
        if version_kind.get(book) != "generated_translation":
            continue

        targets = translation_of.get(book, set())
        source_book = next(iter(targets)) if len(targets) == 1 else None
        generated_version_id = str(version_id.get(book, ""))
        source_version_id = str(version_id.get(source_book, "")) if source_book is not None else ""
        language = str(
            audit._feature(
                data,
                "generated_language",
                book,
                audit._feature(data, "language", book),
            )
        )
        prefix = f"{language.strip().lower()[:2]}_" if language.strip() else ""
        generated_units = units_by_version.get(generated_version_id, [])

        aligned = 0
        seen_targets: set[int] = set()
        for unit in generated_units:
            unit_targets = translation_unit_of.get(unit, set())
            if len(unit_targets) != 1 or source_book is None:
                continue
            target = next(iter(unit_targets))
            generated_id = str(audit._feature(data, "unit_id", unit))
            if prefix and generated_id.startswith(prefix):
                generated_id = generated_id[len(prefix):]
            if (
                target not in seen_targets
                and version_kind.get(target) == "source"
                and str(version_id.get(target, "")) == source_version_id
                and str(audit._feature(data, "source_ref", unit))
                == str(audit._feature(data, "source_ref", target))
                and generated_id == str(audit._feature(data, "unit_id", target))
            ):
                aligned += 1
                seen_targets.add(target)

        records.append(
            {
                "ocp_book": audit._feature(data, "ocp_book", book),
                "version_title": audit._feature(data, "version_title", book),
                "language": language,
                "source_file": audit._feature(data, "source_file", book),
                "marker": audit._feature(data, "generation_marker", book),
                "source_version_title": (
                    audit._feature(data, "version_title", source_book)
                    if source_book is not None
                    else ""
                ),
                "source_version_language": (
                    audit._feature(data, "language", source_book)
                    if source_book is not None
                    else ""
                ),
                "unit_count": len(generated_units),
                "aligned_unit_count": aligned,
            }
        )
    return records


def _generated_provenance_features_ok(data: TFData, node_index: dict[str, list[int]]) -> bool:
    generated_books = [
        node
        for node in node_index.get("book", [])
        if audit._feature(data, "version_kind", node) == "generated_translation"
    ]
    return all(
        audit._feature(data, "generation_marker", node) == "OCP-Trans"
        and audit._feature(data, "generation_method", node) == "llm"
        and audit._feature(data, "generation_model", node)
        == "openrouter/google/gemini-3.7-flash"
        for node in generated_books
    )


def build_conversion_report(source_dir: str | Path, books: list[Book], data: TFData) -> dict:
    """Extend the independent source→TF parity report for generated translations."""

    original_metadata_inventory = _core._metadata_version_inventory
    _core._metadata_version_inventory = _metadata_version_inventory_with_kind
    try:
        report = _core.build_conversion_report(source_dir, books, data)
    finally:
        _core._metadata_version_inventory = original_metadata_inventory

    source_dir = Path(source_dir)
    node_index = audit._node_index(data)
    raw = audit._raw_inventory(source_dir)
    raw_generated = raw["generated_translations"]
    raw_failures = raw["generated_translation_mapping_failures"]
    graph_generated = _graph_generated_translation_inventory(data, node_index)

    alignment_ok = (
        not raw_failures
        and audit._canonical(raw_generated) == audit._canonical(graph_generated)
    )
    provenance_ok = alignment_ok and _generated_provenance_features_ok(data, node_index)

    checks = report["semantic_checks"]
    checks["generated_translation_alignment"] = alignment_ok
    checks["generated_translation_provenance"] = provenance_ok

    source_counts = report["source"]
    source_counts["generated_translation_versions"] = len(raw_generated)
    source_counts["generated_translation_units"] = sum(
        int(record["unit_count"]) for record in raw_generated
    )

    graph_counts = report["graph"]
    graph_counts["generated_translation_versions"] = len(graph_generated)
    graph_counts["generated_translation_units"] = sum(
        int(record["unit_count"]) for record in graph_generated
    )
    graph_counts["translation_of_edges"] = sum(
        len(targets) for targets in data.edge_features.get("translation_of", {}).values()
    )
    graph_counts["translation_unit_of_edges"] = sum(
        len(targets) for targets in data.edge_features.get("translation_unit_of", {}).values()
    )
    graph_counts["synthetic_witnesses"] = sum(
        1
        for node in node_index.get("manuscript", [])
        if audit._feature(data, "synthetic_witness", node, 0) == 1
    )

    by_language: dict[str, dict[str, int]] = {}
    for record in raw_generated:
        language = str(record["language"])
        summary = by_language.setdefault(language, {"versions": 0, "units": 0})
        summary["versions"] += 1
        summary["units"] += int(record["unit_count"])

    generated_units = sum(int(record["unit_count"]) for record in raw_generated)
    aligned_units = sum(int(record["aligned_unit_count"]) for record in raw_generated)
    report["generated_translations"] = {
        "by_language": by_language,
        "versions": len(raw_generated),
        "units": generated_units,
        "aligned_units": aligned_units,
        "alignment_coverage": aligned_units / generated_units if generated_units else 1.0,
    }
    report["diagnostics"]["generated_translation_mapping_failures"] = raw_failures

    failed = [name for name, ok in checks.items() if not ok]
    report["failed_checks"] = failed
    report["status"] = "ok" if not failed else "failed"
    return report


def write_conversion_report(report: dict, path: str | Path) -> None:
    audit.write_conversion_report(report, path)
