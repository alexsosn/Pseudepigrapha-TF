from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .conversion import build_tf_data as _build_core_tf_data
from .graph import TFData
from .model import Book, DocumentMetadata, DocumentMetadataCatalog
from .source import INTRO_FIELDS

INTRO_FEATURES = tuple(f"intro_{name}_json" for name in INTRO_FIELDS)
INTRO_SCALAR_FEATURES = (
    "intro_title_json",
    "intro_version_json",
    "intro_field_order",
    "intro_citation_json",
)
ALL_INTRO_FEATURES = INTRO_SCALAR_FEATURES + INTRO_FEATURES


def _encoded_intro_features(document: DocumentMetadata) -> dict[str, str | int]:
    features: dict[str, str | int] = {
        "has_intro_metadata": 1,
        "intro_title_json": json.dumps(document.title, ensure_ascii=False),
        "intro_version_json": json.dumps(document.version, ensure_ascii=False),
        "intro_field_order": json.dumps(
            [name for name, _ in document.fields], ensure_ascii=False, separators=(",", ":")
        ),
    }
    for name, value in document.fields:
        features[f"intro_{name}_json"] = json.dumps(value, ensure_ascii=False)
    if document.citation is not None:
        features["intro_citation_json"] = json.dumps(document.citation, ensure_ascii=False)
    return features


def _set_feature(data: TFData, name: str, node: int, value: str | int) -> None:
    data.node_features.setdefault(name, {})[node] = value


def _add_work_node(
    data: TFData,
    *,
    node: int,
    ocp_book: str,
    title: str,
    source_file: str,
    anchor: int,
    document: DocumentMetadata | None,
    metadata_only: bool,
) -> None:
    data.node_features["otype"][node] = "work"
    data.edge_features["oslots"][node] = {anchor}
    _set_feature(data, "ocp_book", node, ocp_book)
    _set_feature(data, "title", node, title)
    _set_feature(data, "source_file", node, source_file)
    if metadata_only:
        _set_feature(data, "is_metadata_only_work", node, 1)
    if document is not None:
        for feature, value in _encoded_intro_features(document).items():
            _set_feature(data, feature, node, value)


def _validate_work_layer(data: TFData) -> list[str]:
    """Validate only the newly attached layer; the core graph is already validated."""

    otype = data.node_features.get("otype", {})
    source_files = data.node_features.get("source_file", {})
    ocp_book = data.node_features.get("ocp_book", {})
    version_of = data.edge_features.get("version_of", {})
    work_nodes = {node for node in source_files if otype.get(node) == "work"}
    owners = {
        node for node in source_files
        if otype.get(node) in {"book", "version_metadata"}
    }
    errors: list[str] = []

    for source, targets in version_of.items():
        if source not in owners:
            errors.append(
                f"edge feature version_of source {source} has type {otype.get(source)}; "
                "expected book or version_metadata"
            )
        if len(targets) != 1:
            errors.append(
                f"edge feature version_of source {source} has {len(targets)} targets; expected exactly 1"
            )
            continue
        target = next(iter(targets))
        if target not in work_nodes:
            errors.append(f"edge feature version_of target {target} is not a work node")
        elif ocp_book.get(source) != ocp_book.get(target):
            errors.append(
                f"edge feature version_of source {source} and work {target} disagree on ocp_book"
            )
        elif source_files.get(source) != source_files.get(target):
            errors.append(
                f"edge feature version_of source {source} and work {target} disagree on source_file"
            )

    for source in owners:
        if len(version_of.get(source, set())) != 1:
            errors.append(
                f"{otype.get(source)} node {source} has {len(version_of.get(source, set()))} version_of targets; "
                "expected exactly 1"
            )

    incoming = {work: 0 for work in work_nodes}
    for targets in version_of.values():
        for work in targets:
            if work in incoming:
                incoming[work] += 1
    for work in work_nodes:
        slots = data.edge_features.get("oslots", {}).get(work, set())
        if len(slots) != 1 or any(slot < 1 or slot > data.max_slot for slot in slots):
            errors.append(f"work node {work} does not have one valid technical slot anchor")
        metadata_only = data.node_features.get("is_metadata_only_work", {}).get(work) == 1
        if metadata_only and incoming[work] != 0:
            errors.append(f"metadata-only work node {work} unexpectedly owns a TF version")
        if not metadata_only and incoming[work] < 1:
            errors.append(f"textual work node {work} has no TF version owner")
    return errors


def attach_document_metadata(
    data: TFData,
    books: Iterable[Book],
    catalog: DocumentMetadataCatalog,
) -> TFData:
    """Attach one document/work node per OCP work without duplicating long metadata.

    Text-Fabric 13.1 does not preserve raw carriage returns in ordinary string
    features. Source strings are therefore JSON-encoded once on the work node;
    researcher-facing APIs decode them back to the exact upstream values.
    """

    books = list(books)
    if "version_of" in data.edge_features:
        raise ValueError("cannot attach document metadata: graph already has version_of edges")
    if data.max_slot < 1:
        raise ValueError("cannot attach document metadata without a Text-Fabric word slot anchor")

    documents_by_source: dict[str, DocumentMetadata] = {}
    for document in catalog.documents:
        if document.source_file in documents_by_source:
            raise ValueError(f"duplicate document metadata source file: {document.source_file}")
        documents_by_source[document.source_file] = document

    owners_by_source: dict[str, list[int]] = {}
    otype = data.node_features["otype"]
    source_files = data.node_features.get("source_file", {})
    for node, source_value in source_files.items():
        kind = otype.get(node)
        if kind not in {"book", "version_metadata"}:
            continue
        source_file = str(source_value)
        if not source_file:
            raise ValueError(f"{kind} node {node} has no source_file for work ownership")
        owners_by_source.setdefault(source_file, []).append(node)

    seen_sources: set[str] = set()
    seen_work_ids: set[str] = set()
    version_of: dict[int, set[int]] = {}
    # Core validation guarantees contiguous node ids, so length is the current max.
    next_node = len(otype) + 1

    for book in books:
        source_file = book.source_path
        if not source_file:
            raise ValueError(f"{book.filename}: book has no source_path for document metadata mapping")
        if source_file in seen_sources:
            raise ValueError(f"duplicate parsed source path for document metadata mapping: {source_file}")
        if book.filename in seen_work_ids:
            raise ValueError(f"duplicate OCP work identifier: {book.filename}")
        owners = owners_by_source.get(source_file, [])
        if not owners:
            raise ValueError(f"{source_file}: parsed work has no TF version owner")
        document = documents_by_source.get(source_file)
        if document is not None and document.xml_empty:
            raise ValueError(f"{source_file}: metadata marks XML empty but a parsed Book exists")
        owner_slots = [
            slot
            for owner in owners
            for slot in data.edge_features.get("oslots", {}).get(owner, set())
        ]
        if not owner_slots:
            raise ValueError(f"{source_file}: parsed work has no TF slot anchor")
        work_node = next_node
        next_node += 1
        _add_work_node(
            data,
            node=work_node,
            ocp_book=book.filename,
            title=book.title,
            source_file=source_file,
            anchor=min(owner_slots),
            document=document,
            metadata_only=False,
        )
        for owner in owners:
            version_of[owner] = {work_node}
        seen_sources.add(source_file)
        seen_work_ids.add(book.filename)

    for document in catalog.documents:
        if document.source_file in seen_sources:
            continue
        if not document.xml_empty:
            raise ValueError(
                f"{document.source_file}: document metadata has non-empty XML but no parsed Book"
            )
        work_id = Path(document.source_file).stem
        if work_id in seen_work_ids:
            raise ValueError(f"duplicate OCP work identifier from metadata-only XML: {work_id}")
        work_node = next_node
        next_node += 1
        _add_work_node(
            data,
            node=work_node,
            ocp_book=work_id,
            title=document.title,
            source_file=document.source_file,
            anchor=1,
            document=document,
            metadata_only=True,
        )
        seen_sources.add(document.source_file)
        seen_work_ids.add(work_id)

    data.edge_features["version_of"] = version_of

    # Always serialize the complete public metadata feature vocabulary whenever
    # the work layer is enabled, so selective loading can distinguish an absent
    # value from an unshipped feature file.
    for feature in ALL_INTRO_FEATURES:
        data.node_features.setdefault(feature, {})
    data.node_features.setdefault("has_intro_metadata", {})
    data.node_features.setdefault("is_metadata_only_work", {})

    data.metadata[""]["introMetadataFile"] = "intros.json"
    data.metadata[""]["introExportMetaJson"] = json.dumps(
        dict(catalog.meta), ensure_ascii=False, separators=(",", ":")
    )
    data.metadata["otext"]["fmt:work-default"] = "{title}"
    data.metadata["version_of"] = {
        "valueType": "str",
        "description": "OCP textual/version-metadata owner to its document-level work node",
    }
    data.metadata["has_intro_metadata"] = {
        "valueType": "int",
        "description": "1 when this work has a public upstream intros.json document record",
    }
    data.metadata["is_metadata_only_work"] = {
        "valueType": "int",
        "description": "1 when the OCP work has public document metadata but its sibling XML is empty",
    }
    data.metadata["intro_field_order"] = {
        "valueType": "str",
        "description": "JSON array preserving upstream intros.json body-field order",
    }
    data.metadata["intro_title_json"] = {
        "valueType": "str",
        "description": "JSON-encoded exact upstream intros.json document title",
    }
    data.metadata["intro_version_json"] = {
        "valueType": "str",
        "description": "JSON-encoded exact upstream intros.json document version scalar",
    }
    data.metadata["intro_citation_json"] = {
        "valueType": "str",
        "description": "JSON-encoded exact upstream per-document citation HTML",
    }
    for field in INTRO_FIELDS:
        feature = f"intro_{field}_json"
        data.metadata[feature] = {
            "valueType": "str",
            "description": f"JSON-encoded exact upstream intros.json {field} HTML/text",
        }

    failures = _validate_work_layer(data)
    if failures:
        raise ValueError("invalid document-enriched Text-Fabric graph: " + "; ".join(failures))
    return data


def build_tf_data(
    books: Iterable[Book],
    *,
    document_metadata: DocumentMetadataCatalog | None = None,
    upstream_repository: str = "https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha",
    upstream_commit: str = "",
    converter_version: str = "0.1.0",
) -> TFData:
    """Build the canonical corpus and optionally add document-level scholarship."""

    books = list(books)
    data = _build_core_tf_data(
        books,
        upstream_repository=upstream_repository,
        upstream_commit=upstream_commit,
        converter_version=converter_version,
    )
    if document_metadata is None:
        return data
    return attach_document_metadata(data, books, document_metadata)
