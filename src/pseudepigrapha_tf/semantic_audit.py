from __future__ import annotations

import json
from pathlib import Path

from . import audit as base
from .graph import TFData
from .model import Book


def _metadata_version_inventory(data: TFData) -> tuple[list[dict], list[dict]]:
    versions: list[dict] = []
    division_specs: list[dict] = []
    for node in base._nodes(data, "version_metadata"):
        ocp_book = base._feature(data, "ocp_book", node)
        version_title = base._feature(data, "version_title", node)
        versions.append({"ocp_book": ocp_book, "version_title": version_title})
        labels = json.loads(base._feature(data, "division_labels", node, "[]"))
        delimiters = json.loads(base._feature(data, "division_delimiters", node, "[]"))
        texts = json.loads(base._feature(data, "division_texts", node, "[]"))
        for index, label in enumerate(labels, 1):
            division_specs.append(
                {
                    "ocp_book": ocp_book,
                    "version_title": version_title,
                    "index": index,
                    "label": label,
                    "delimiter": delimiters[index - 1] if index <= len(delimiters) else "",
                    "text": texts[index - 1] if index <= len(texts) else "",
                }
            )
    return versions, division_specs


def _section_coverage_ok(data: TFData) -> bool:
    """Verify exactly one book/chapter/verse per primary slot in linear time."""

    oslots = data.edge_features.get("oslots", {})
    max_slot = data.max_slot
    for kind in ("book", "chapter", "verse"):
        coverage = bytearray(max_slot + 1)
        for node in base._nodes(data, kind):
            for slot in oslots.get(node, set()):
                if slot > max_slot:
                    return False
                if coverage[slot] < 2:
                    coverage[slot] += 1
        if any(value != 1 for value in coverage[1:]):
            return False
    return True


def _section_addresses_unique(data: TFData) -> bool:
    """Verify unique section addresses without repeated global section scans."""

    oslots = data.edge_features.get("oslots", {})
    slot_book: dict[int, int] = {}
    slot_chapter: dict[int, int] = {}

    for node in base._nodes(data, "book"):
        for slot in oslots.get(node, set()):
            if slot in slot_book:
                return False
            slot_book[slot] = node
    for node in base._nodes(data, "chapter"):
        for slot in oslots.get(node, set()):
            if slot in slot_chapter:
                return False
            slot_chapter[slot] = node

    seen: set[tuple[str, str, str]] = set()
    for verse in base._nodes(data, "verse"):
        slots = oslots.get(verse, set())
        if not slots:
            continue
        book_nodes = {slot_book.get(slot) for slot in slots}
        chapter_nodes = {slot_chapter.get(slot) for slot in slots}
        if None in book_nodes or None in chapter_nodes or len(book_nodes) != 1 or len(chapter_nodes) != 1:
            return False
        book_node = next(iter(book_nodes))
        chapter_node = next(iter(chapter_nodes))
        address = (
            str(base._feature(data, "book", book_node)),
            str(base._feature(data, "chapter", chapter_node)),
            str(base._feature(data, "verse", verse)),
        )
        if address in seen:
            return False
        seen.add(address)
    return True


def build_conversion_report(source_dir: str | Path, books: list[Book], data: TFData) -> dict:
    """Build an independent source→TF parity report, including metadata-only versions."""

    raw = base._raw_inventory(Path(source_dir))
    graph = base._graph_inventory(data)
    metadata_versions, metadata_specs = _metadata_version_inventory(data)
    graph["versions"].extend(metadata_versions)
    graph["division_specs"].extend(metadata_specs)

    primary_ok, alternative_ok = base._reconstruction_checks(data)
    source_hashes = {record["file"]: record["sha256"] for record in raw["files"]}
    model_hashes = {book.source_path: book.source_sha256 for book in books}

    checks = {
        "source_hashes": source_hashes == model_hashes,
        "versions": base._canonical(raw["versions"]) == base._canonical(graph["versions"]),
        "division_specs": base._canonical(raw["division_specs"]) == base._canonical(graph["division_specs"]),
        "divisions": base._canonical(raw["divs"]) == base._canonical(graph["divs"]),
        "units": base._canonical(raw["units"]) == base._canonical(graph["units"]),
        "reading_payloads": base._canonical(raw["readings"]) == base._canonical(graph["readings"]),
        "manuscripts": base._canonical(raw["manuscripts"]) == base._canonical(graph["manuscripts"]),
        "resources": base._canonical(raw["resources"]) == base._canonical(graph["resources"]),
        "annotated_words": base._canonical(raw["annotated_words"]) == base._canonical(graph["annotated_words"]),
        "primary_reconstruction": primary_ok,
        "alternative_reconstruction": alternative_ok,
        "unit_parent_linkage": base._parent_linkage_ok(data),
        "section_coverage": _section_coverage_ok(data),
        "section_addresses_unique": _section_addresses_unique(data),
    }

    source_counts = {
        "files": len(raw["files"]),
        "versions": len(raw["versions"]),
        "divisions": len(raw["divs"]),
        "units": len(raw["units"]),
        "readings": len(raw["readings"]),
        "manuscripts": len(raw["manuscripts"]),
        "resources": len(raw["resources"]),
        "annotated_words": len(raw["annotated_words"]),
    }
    metadata_count = len(base._nodes(data, "version_metadata"))
    graph_counts = {
        "slots": data.max_slot,
        "nodes": data.max_node,
        "oslots_edges": data.oslots_edge_count,
        "versions": len(base._nodes(data, "book")) + metadata_count,
        "metadata_only_versions": metadata_count,
        "divisions": len(base._nodes(data, "div")),
        "units": len(base._nodes(data, "unit")),
        "readings": len(base._nodes(data, "reading")),
        "variant_words": len(base._nodes(data, "variant_word")),
        "manuscripts": len(
            [
                node
                for node in base._nodes(data, "manuscript")
                if base._feature(data, "undefined_manuscript", node, 0) != 1
            ]
        ),
        "resources": len(base._nodes(data, "resource")),
        "witness_edges": sum(
            len(targets) for targets in data.edge_features.get("witness", {}).values()
        ),
    }

    generic = data.metadata.get("", {})
    failed = [name for name, ok in checks.items() if not ok]
    return {
        "status": "ok" if not failed else "failed",
        "failed_checks": failed,
        "semantic_checks": checks,
        "source": source_counts,
        "graph": graph_counts,
        "source_sha256": source_hashes,
        "provenance": {
            "upstream_repository": generic.get("upstreamRepository", ""),
            "upstream_commit": generic.get("upstreamCommit", ""),
            "converter_version": generic.get("converterVersion", ""),
        },
    }


def write_conversion_report(report: dict, path: str | Path) -> None:
    base.write_conversion_report(report, path)
