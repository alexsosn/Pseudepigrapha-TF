from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

from . import audit as base
from .graph import TFData
from .model import Book, DivisionSpec


def _metadata_version_inventory(data: TFData) -> tuple[list[dict], list[dict]]:
    versions: list[dict] = []
    division_specs: list[dict] = []
    for node in base._nodes(data, "version_metadata"):
        ocp_book = base._feature(data, "ocp_book", node)
        version_title = base._feature(data, "version_title", node)
        versions.append(
            {
                "ocp_book": ocp_book,
                "title": base._feature(data, "title", node),
                "text_structure": base._feature(data, "text_structure", node),
                "version_title": version_title,
                "author": base._feature(data, "author", node),
                "language": base._feature(data, "language", node),
                "fragment": base._feature(data, "version_fragment", node),
                "source_file": base._feature(data, "source_file", node),
                "source_sha256": base._feature(data, "source_sha256", node),
            }
        )
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


def _raw_special_structure_inventory(source_dir: Path) -> tuple[list[dict], list[dict]]:
    """Read preserved source anomalies independently of the parsed model.

    The source tree is scanned once for both supported anomalies so adding
    parity checks does not introduce one full XML pass per anomaly type.
    """

    ellipses: list[dict] = []
    orphan_readings: list[dict] = []

    def walk_div(
        div: ET.Element,
        *,
        ocp_book: str,
        version_title: str,
        specs: tuple[DivisionSpec, ...],
        path: tuple[str, ...],
    ) -> None:
        dpath = path + (div.get("number", ""),)
        source_ref = base._reference(dpath, specs)
        for child_index, child in enumerate(list(div), 1):
            if child.tag == "elipsis":
                ellipses.append(
                    {
                        "ocp_book": ocp_book,
                        "version_title": version_title,
                        "source_ref": source_ref,
                        "parent_source_ref": source_ref,
                        "source_tag": child.tag,
                        "text": base._plain_text(child),
                        "source_child_index": child_index,
                    }
                )
            elif child.tag == "reading":
                mss = child.get("mss", "")
                orphan_readings.append(
                    {
                        "ocp_book": ocp_book,
                        "version_title": version_title,
                        "source_ref": source_ref,
                        "parent_source_ref": source_ref,
                        "source_tag": child.tag,
                        "source_child_index": child_index,
                        "option": child.get("option", ""),
                        "mss": mss.strip(),
                        "witnesses": sorted(part for part in mss.split() if part),
                        "linebreak": child.get("linebreak", ""),
                        "indent": child.get("indent", ""),
                        "text": base._plain_text(child),
                        "xml": base._inner_xml(child),
                    }
                )
            elif child.tag == "div":
                walk_div(
                    child,
                    ocp_book=ocp_book,
                    version_title=version_title,
                    specs=specs,
                    path=dpath,
                )

    for path in sorted(source_dir.glob("*.xml")):
        data = path.read_bytes()
        if path.name.startswith(".") or not data.strip():
            continue
        root = ET.fromstring(data)
        ocp_book = root.get("filename", "")
        for version in root.findall("version"):
            divisions = version.find("divisions")
            specs = tuple(
                DivisionSpec(d.get("label", ""), d.get("delimiter", ""), base._plain_text(d))
                for d in (divisions.findall("division") if divisions is not None else [])
            )
            text = version.find("text")
            if text is None:
                continue
            for div in text.findall("div"):
                walk_div(
                    div,
                    ocp_book=ocp_book,
                    version_title=version.get("title", ""),
                    specs=specs,
                    path=(),
                )
    return ellipses, orphan_readings


def _parent_source_ref(data: TFData, node: int) -> str:
    targets = data.edge_features.get("parent", {}).get(node, set())
    otype = data.node_features.get("otype", {})
    if len(targets) != 1:
        return "__INVALID_PARENT__"
    target = next(iter(targets))
    if otype.get(target) != "div":
        return "__INVALID_PARENT__"
    return str(base._feature(data, "source_ref", target))


def _graph_ellipsis_inventory(data: TFData) -> list[dict]:
    return [
        {
            "ocp_book": base._feature(data, "ocp_book", node),
            "version_title": base._feature(data, "version_title", node),
            "source_ref": base._feature(data, "source_ref", node),
            "parent_source_ref": _parent_source_ref(data, node),
            "source_tag": base._feature(data, "source_tag", node),
            "text": base._feature(data, "ellipsis_text", node),
            "source_child_index": base._feature(data, "source_child_index", node, 0),
        }
        for node in base._nodes(data, "ellipsis")
    ]


def _graph_orphan_reading_inventory(data: TFData) -> list[dict]:
    records: list[dict] = []
    witness_edges = data.edge_features.get("witness", {})
    for node in base._nodes(data, "orphan_reading"):
        mss = str(base._feature(data, "mss", node))
        records.append(
            {
                "ocp_book": base._feature(data, "ocp_book", node),
                "version_title": base._feature(data, "version_title", node),
                "source_ref": base._feature(data, "source_ref", node),
                "parent_source_ref": _parent_source_ref(data, node),
                "source_tag": base._feature(data, "source_tag", node),
                "source_child_index": base._feature(data, "source_child_index", node, 0),
                "option": base._feature(data, "reading_option_source", node),
                "mss": mss,
                "witnesses": sorted(
                    str(base._feature(data, "ms_abbrev", target))
                    for target in witness_edges.get(node, set())
                ),
                "linebreak": base._feature(data, "linebreak", node),
                "indent": base._feature(data, "indent", node),
                "text": base._feature(data, "reading_text", node),
                "xml": base._feature(data, "reading_xml", node),
            }
        )
    return records


def _technical_parent_anchors_ok(data: TFData, node_type: str) -> bool:
    parent_edge = data.edge_features.get("parent", {})
    oslots = data.edge_features.get("oslots", {})
    otype = data.node_features.get("otype", {})
    for node in base._nodes(data, node_type):
        slots = oslots.get(node, set())
        targets = parent_edge.get(node, set())
        if len(slots) != 1 or len(targets) != 1:
            return False
        parent = next(iter(targets))
        if otype.get(parent) != "div" or not slots.issubset(oslots.get(parent, set())):
            return False
    return True


def _witness_targets_owned_by_source_version(data: TFData, node_type: str) -> bool:
    """Require anomaly witness edges to stay inside their exact source version."""

    witness_edges = data.edge_features.get("witness", {})
    otype = data.node_features.get("otype", {})
    version_ids = data.node_features.get("version_id", {})
    for node in base._nodes(data, node_type):
        source_version = version_ids.get(node, "")
        if not source_version:
            return False
        for target in witness_edges.get(node, set()):
            if otype.get(target) != "manuscript" or version_ids.get(target, "") != source_version:
                return False
    return True


def _ownership_edge_ok(
    data: TFData,
    *,
    source_type: str,
    edge_name: str,
    target_types: frozenset[str],
    identity_features: tuple[str, ...],
) -> bool:
    """Validate exact one-owner edges against independently stamped identity."""

    otype = data.node_features.get("otype", {})
    edge = data.edge_features.get(edge_name, {})
    version_ids = data.node_features.get("version_id", {})

    for source in base._nodes(data, source_type):
        targets = edge.get(source, set())
        if len(targets) != 1:
            return False
        target = next(iter(targets))
        if otype.get(target) not in target_types:
            return False
        source_version = version_ids.get(source, "")
        if not source_version or source_version != version_ids.get(target, ""):
            return False
        for feature in identity_features:
            source_value = data.node_features.get(feature, {}).get(source, "")
            target_value = data.node_features.get(feature, {}).get(target, "")
            if source_value != target_value:
                return False
    return True


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


def _section_address_records(data: TFData) -> list[tuple[tuple[str, str, str], int, str]] | None:
    """Resolve every verse to its TF address and exact upstream source ref."""

    oslots = data.edge_features.get("oslots", {})
    slot_book: dict[int, int] = {}
    slot_chapter: dict[int, int] = {}

    for node in base._nodes(data, "book"):
        for slot in oslots.get(node, set()):
            if slot in slot_book:
                return None
            slot_book[slot] = node
    for node in base._nodes(data, "chapter"):
        for slot in oslots.get(node, set()):
            if slot in slot_chapter:
                return None
            slot_chapter[slot] = node

    records: list[tuple[tuple[str, str, str], int, str]] = []
    for verse in base._nodes(data, "verse"):
        slots = oslots.get(verse, set())
        if not slots:
            continue
        book_nodes = {slot_book.get(slot) for slot in slots}
        chapter_nodes = {slot_chapter.get(slot) for slot in slots}
        if None in book_nodes or None in chapter_nodes or len(book_nodes) != 1 or len(chapter_nodes) != 1:
            return None
        book_node = next(iter(book_nodes))
        chapter_node = next(iter(chapter_nodes))
        address = (
            str(base._feature(data, "book", book_node)),
            str(base._feature(data, "chapter", chapter_node)),
            str(base._feature(data, "verse", verse)),
        )
        records.append((address, verse, str(base._feature(data, "source_ref", verse))))
    return records


def _section_address_collisions(data: TFData) -> list[dict]:
    """Return duplicate TF section addresses with enough provenance to debug them."""

    records = _section_address_records(data)
    if records is None:
        return []
    grouped: dict[tuple[str, str, str], list[tuple[int, str]]] = {}
    for address, node, source_ref in records:
        grouped.setdefault(address, []).append((node, source_ref))
    return [
        {
            "address": list(address),
            "nodes": [node for node, _ in entries],
            "source_refs": [source_ref for _, source_ref in entries],
        }
        for address, entries in grouped.items()
        if len(entries) > 1
    ]


def _section_addresses_unique(data: TFData) -> bool:
    """Verify every textual section has a unique TF address."""

    records = _section_address_records(data)
    if records is None:
        return False
    seen: set[tuple[str, str, str]] = set()
    for address, _, _ in records:
        if address in seen:
            return False
        seen.add(address)
    return True


def build_conversion_report(source_dir: str | Path, books: list[Book], data: TFData) -> dict:
    """Build an independent source→TF parity report, including source anomalies."""

    source_dir = Path(source_dir)
    raw = base._raw_inventory(source_dir)
    graph = base._graph_inventory(data)
    metadata_versions, metadata_specs = _metadata_version_inventory(data)
    graph["versions"].extend(metadata_versions)
    graph["division_specs"].extend(metadata_specs)
    raw_ellipses, raw_orphan_readings = _raw_special_structure_inventory(source_dir)
    graph_ellipses = _graph_ellipsis_inventory(data)
    graph_orphan_readings = _graph_orphan_reading_inventory(data)

    primary_ok, alternative_ok = base._reconstruction_checks(data)
    source_hashes = {record["file"]: record["sha256"] for record in raw["files"]}
    model_hashes = {book.source_path: book.source_sha256 for book in books}
    section_address_collisions = _section_address_collisions(data)

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
        "ellipses": base._canonical(raw_ellipses) == base._canonical(graph_ellipses),
        "ellipsis_anchors": _technical_parent_anchors_ok(data, "ellipsis"),
        "orphan_readings": base._canonical(raw_orphan_readings) == base._canonical(graph_orphan_readings),
        "orphan_reading_anchors": _technical_parent_anchors_ok(data, "orphan_reading"),
        "orphan_witness_ownership": _witness_targets_owned_by_source_version(data, "orphan_reading"),
        "primary_reconstruction": primary_ok,
        "alternative_reconstruction": alternative_ok,
        "unit_parent_linkage": base._parent_linkage_ok(data),
        "reading_ownership": _ownership_edge_ok(
            data,
            source_type="reading",
            edge_name="reading_of",
            target_types=frozenset({"unit"}),
            identity_features=("ocp_book", "version_title", "source_ref", "unit_id"),
        ),
        "manuscript_ownership": _ownership_edge_ok(
            data,
            source_type="manuscript",
            edge_name="manuscript_of",
            target_types=frozenset({"book", "version_metadata"}),
            identity_features=("ocp_book", "version_title"),
        ),
        "resource_ownership": _ownership_edge_ok(
            data,
            source_type="resource",
            edge_name="resource_of",
            target_types=frozenset({"book", "version_metadata"}),
            identity_features=("ocp_book", "version_title"),
        ),
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
        "ellipses": len(raw_ellipses),
        "orphan_readings": len(raw_orphan_readings),
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
        "ellipses": len(base._nodes(data, "ellipsis")),
        "orphan_readings": len(base._nodes(data, "orphan_reading")),
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
        "diagnostics": {
            "duplicate_section_addresses": section_address_collisions,
        },
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
