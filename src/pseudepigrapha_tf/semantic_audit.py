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


def build_conversion_report(source_dir: str | Path, books: list[Book], data: TFData) -> dict:
    """Run the base semantic audit, including versions that intentionally have no text."""

    report = base.build_conversion_report(source_dir, books, data)
    raw = base._raw_inventory(Path(source_dir))
    graph = base._graph_inventory(data)
    metadata_versions, metadata_specs = _metadata_version_inventory(data)
    graph["versions"].extend(metadata_versions)
    graph["division_specs"].extend(metadata_specs)

    report["semantic_checks"]["versions"] = (
        base._canonical(raw["versions"]) == base._canonical(graph["versions"])
    )
    report["semantic_checks"]["division_specs"] = (
        base._canonical(raw["division_specs"]) == base._canonical(graph["division_specs"])
    )

    metadata_count = len(base._nodes(data, "version_metadata"))
    report["graph"]["metadata_only_versions"] = metadata_count
    report["graph"]["versions"] = len(base._nodes(data, "book")) + metadata_count

    failed = [name for name, ok in report["semantic_checks"].items() if not ok]
    report["failed_checks"] = failed
    report["status"] = "ok" if not failed else "failed"
    return report


def write_conversion_report(report: dict, path: str | Path) -> None:
    base.write_conversion_report(report, path)
