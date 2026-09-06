from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from .graph import TFData
from .model import Book
from .semantic_audit import build_conversion_report as _build_core_conversion_report
from .semantic_audit import write_conversion_report
from .source import INTRO_FIELDS


def _raw_document_metadata(source_dir: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Read raw committed intros.json independently of the conversion source model."""

    path = source_dir / "intros.json"
    if not path.is_file():
        return {}, []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("raw intros.json root must be an object during semantic audit")
    meta = payload.get("_meta", {})
    documents = payload.get("documents", {})
    if not isinstance(meta, dict) or not isinstance(documents, dict):
        raise ValueError("raw intros.json _meta/documents must be objects during semantic audit")

    records: list[dict[str, object]] = []
    for source_file, entry in documents.items():
        if not isinstance(entry, dict):
            raise ValueError(f"raw intro entry {source_file!r} must be an object")
        fields = entry.get("fields", {})
        if not isinstance(fields, dict):
            raise ValueError(f"raw intro fields {source_file!r} must be an object")
        records.append(
            {
                "source_file": source_file,
                "title": entry.get("title"),
                "version": entry.get("version"),
                "fields": list(fields.items()),
                "citation": entry.get("citation"),
            }
        )
    return meta, sorted(records, key=lambda record: str(record["source_file"]))


def _decode_feature(
    data: TFData,
    feature: str,
    node: int,
    errors: list[dict[str, object]],
    *,
    required: bool = False,
):
    raw = data.node_features.get(feature, {}).get(node)
    if raw is None:
        if required:
            errors.append({"node": node, "feature": feature, "error": "missing"})
        return None
    try:
        return json.loads(str(raw))
    except json.JSONDecodeError:
        errors.append({"node": node, "feature": feature, "error": "invalid_json"})
        return None


def _graph_document_metadata(data: TFData) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Decode graph metadata without consulting the parsed metadata catalog."""

    errors: list[dict[str, object]] = []
    source_files = data.node_features.get("source_file", {})
    titles = data.node_features.get("intro_title_json", {})
    field_orders = data.node_features.get("intro_field_order", {})
    citations = data.node_features.get("intro_citation_json", {})
    records: list[dict[str, object]] = []

    for node in sorted(titles):
        source_file = str(source_files.get(node, ""))
        title = _decode_feature(data, "intro_title_json", node, errors, required=True)
        version = _decode_feature(data, "intro_version_json", node, errors, required=True)
        order = _decode_feature(data, "intro_field_order", node, errors, required=True)
        if not isinstance(order, list) or any(
            not isinstance(name, str) or name not in INTRO_FIELDS for name in order
        ):
            errors.append({"node": node, "feature": "intro_field_order", "error": "invalid_value"})
            order = []
        if len(order) != len(set(order)):
            errors.append({"node": node, "feature": "intro_field_order", "error": "duplicate_field"})

        fields: list[tuple[str, object]] = []
        for name in order:
            value = _decode_feature(data, f"intro_{name}_json", node, errors, required=True)
            fields.append((name, value))
        citation = (
            _decode_feature(data, "intro_citation_json", node, errors)
            if node in citations
            else None
        )
        records.append(
            {
                "source_file": source_file,
                "title": title,
                "version": version,
                "fields": fields,
                "citation": citation,
            }
        )
    return sorted(records, key=lambda record: str(record["source_file"])), errors


def _record_digest(record: dict[str, object] | None) -> str:
    if record is None:
        return ""
    payload = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _metadata_mismatches(
    raw_records: list[dict[str, object]],
    graph_records: list[dict[str, object]],
) -> list[dict[str, str]]:
    raw = {str(record["source_file"]): record for record in raw_records}
    graph = {str(record["source_file"]): record for record in graph_records}
    diagnostics: list[dict[str, str]] = []
    for source_file in sorted(set(raw) | set(graph)):
        raw_record = raw.get(source_file)
        graph_record = graph.get(source_file)
        if raw_record == graph_record:
            continue
        kind = "changed"
        if raw_record is None:
            kind = "extra_graph"
        elif graph_record is None:
            kind = "missing_graph"
        diagnostics.append(
            {
                "source_file": source_file,
                "kind": kind,
                "source_sha256": _record_digest(raw_record),
                "graph_sha256": _record_digest(graph_record),
            }
        )
    return diagnostics


def _work_version_ownership_ok(data: TFData) -> bool:
    otype = data.node_features.get("otype", {})
    source_files = data.node_features.get("source_file", {})
    ocp_books = data.node_features.get("ocp_book", {})
    version_of = data.edge_features.get("version_of", {})
    work_nodes = {
        node for node in source_files
        if otype.get(node) == "work"
    }
    owners = {
        node for node in source_files
        if otype.get(node) in {"book", "version_metadata"}
    }

    # Preserve compatibility for callers auditing a core graph that predates or
    # deliberately omits the optional document-work layer.
    if not work_nodes and not version_of:
        return True

    incoming: Counter[int] = Counter()
    for owner in owners:
        targets = version_of.get(owner, set())
        if len(targets) != 1:
            return False
        work = next(iter(targets))
        if work not in work_nodes:
            return False
        if source_files.get(owner) != source_files.get(work):
            return False
        if ocp_books.get(owner) != ocp_books.get(work):
            return False
        incoming[work] += 1

    if any(source not in owners for source in version_of):
        return False
    for work in work_nodes:
        metadata_only = data.node_features.get("is_metadata_only_work", {}).get(work) == 1
        if metadata_only:
            if incoming[work] != 0:
                return False
        elif incoming[work] < 1:
            return False
    return True


def _field_counts(records: list[dict[str, object]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        for name, _ in record["fields"]:  # type: ignore[index]
            counts[str(name)] += 1
    return dict(sorted(counts.items()))


def build_conversion_report(source_dir: str | Path, books: list[Book], data: TFData) -> dict:
    """Extend the core XML parity report with independent scholarly-metadata parity."""

    source_dir = Path(source_dir)
    report = _build_core_conversion_report(source_dir, books, data)
    raw_meta, raw_records = _raw_document_metadata(source_dir)
    graph_records, graph_decode_errors = _graph_document_metadata(data)
    mismatches = _metadata_mismatches(raw_records, graph_records)

    generic = data.metadata.get("", {})
    try:
        graph_meta = json.loads(generic.get("introExportMetaJson", "{}"))
    except json.JSONDecodeError:
        graph_meta = None

    checks = report["semantic_checks"]
    checks["document_metadata_exact"] = not mismatches and not graph_decode_errors
    checks["document_metadata_export_meta"] = graph_meta == raw_meta
    checks["work_version_ownership"] = _work_version_ownership_ok(data)

    report["source"]["document_metadata_documents"] = len(raw_records)
    report["source"]["document_metadata_citations"] = sum(
        1 for record in raw_records if record.get("citation") is not None
    )
    report["source"]["document_metadata_fields"] = _field_counts(raw_records)
    report["graph"]["document_metadata_documents"] = len(graph_records)
    report["graph"]["document_metadata_citations"] = sum(
        1 for record in graph_records if record.get("citation") is not None
    )
    report["graph"]["document_metadata_fields"] = _field_counts(graph_records)
    report["graph"]["works"] = sum(
        1 for node in data.node_features.get("source_file", {})
        if data.node_features.get("otype", {}).get(node) == "work"
    )
    report["graph"]["metadata_only_works"] = len(data.node_features.get("is_metadata_only_work", {}))

    diagnostics = report.setdefault("diagnostics", {})
    diagnostics["document_metadata_mismatches"] = mismatches
    diagnostics["document_metadata_decode_errors"] = graph_decode_errors

    failed = [name for name, ok in checks.items() if not ok]
    report["failed_checks"] = failed
    report["status"] = "ok" if not failed else "failed"
    report["provenance"]["intro_export_meta"] = raw_meta
    return report


__all__ = ["build_conversion_report", "write_conversion_report"]
