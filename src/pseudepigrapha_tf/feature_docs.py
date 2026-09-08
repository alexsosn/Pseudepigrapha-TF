from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .classifications import (
    HistoricalClassifications,
    attach_historical_classifications,
    load_historical_classifications,
)
from .feature_contract import DOCUMENTATION_CATEGORIES, with_documentation_category
from .graph import EDGE_DESCRIPTIONS, EDGE_FEATURE_CONTRACTS, FEATURE_DESCRIPTIONS, INT_FEATURES, TFData
from .metadata import (
    ALL_INTRO_FEATURES,
    PublicMetadataCorpus,
    PublicMetadataDocument,
    attach_public_metadata,
)
from .writer import (
    _edge_features_with_api_dependencies,
    _metadata_with_serialized_features,
    _node_features_with_format_dependencies,
)


def _supported_node_descriptors_from_probe(
    data: TFData,
    names: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    """Derive canonical supported node types from the real emitter probe."""

    otype = data.node_features.get("otype", {})
    layer_node_types = tuple(sorted({str(kind) for kind in otype.values() if kind != "word"}))
    if not layer_node_types:
        raise ValueError("feature documentation emitter probe produced no non-slot node type")

    result: dict[str, dict[str, Any]] = {}
    for name in names:
        observed = _observed_node_types(data, data.node_features.get(name, {}))
        result[name] = {
            "metadata": with_documentation_category(
                name,
                kind="node",
                metadata=data.metadata[name],
            ),
            "supportedNodeTypes": observed or layer_node_types,
        }
    return result


def _public_metadata_from_emitter() -> dict[str, dict[str, Any]]:
    """Obtain supported public-metadata descriptors from the real emitter."""

    data = TFData(
        node_features={"otype": {1: "word"}},
        edge_features={"oslots": {}},
        metadata={},
    )
    metadata = PublicMetadataCorpus(
        documents={
            "__feature_docs__.xml": PublicMetadataDocument(
                filename="__feature_docs__.xml",
                title="feature documentation probe",
                version="probe",
                citation=None,
                citation_present=False,
                fields={},
            )
        },
        source_sha256="0" * 64,
        source_meta={},
    )
    attach_public_metadata(data, metadata)
    names = (*ALL_INTRO_FEATURES, "intro_label")
    return _supported_node_descriptors_from_probe(data, tuple(names))


def _historical_metadata_from_emitter() -> dict[str, dict[str, Any]]:
    """Obtain supported historical-classification descriptors from the real emitter."""

    classifications = load_historical_classifications()
    works = sorted(classifications.documents)
    otype: dict[int, str | int] = {1: "word"}
    ocp_book: dict[int, str | int] = {}
    oslots: dict[int, set[int]] = {}
    for node, work_id in enumerate(works, start=2):
        otype[node] = "document_metadata"
        ocp_book[node] = work_id
        oslots[node] = {1}
    data = TFData(
        node_features={"otype": otype, "ocp_book": ocp_book},
        edge_features={"oslots": oslots},
        metadata={},
    )
    attach_historical_classifications(data, classifications)
    names = tuple(
        name for name in HistoricalClassifications.REQUIRED_FEATURES if name != "ocp_book"
    )
    return _supported_node_descriptors_from_probe(data, tuple(names))


def _supported_node_descriptors() -> dict[str, dict[str, Any]]:
    """Return canonical emitter descriptors for supported optional metadata layers."""

    result = _public_metadata_from_emitter()
    result.update(_historical_metadata_from_emitter())
    return result


def edge_feature_contracts() -> dict[str, dict[str, Any]]:
    """Return a deterministic read-only copy of supported edge semantics."""

    result: dict[str, dict[str, Any]] = {}
    for name in sorted(EDGE_FEATURE_CONTRACTS):
        source = EDGE_FEATURE_CONTRACTS[name]
        item: dict[str, Any] = {
            "sourceTypes": tuple(sorted(source["sourceTypes"])),
            "targetTypes": tuple(sorted(source["targetTypes"])),
            "cardinality": str(source["cardinality"]),
            "technicalSupport": bool(source.get("technicalSupport", False)),
            "corpusDependent": bool(source.get("corpusDependent", False)),
            "edgeValues": False,
            "description": EDGE_DESCRIPTIONS[name],
        }
        if source.get("sourceQualifier"):
            item["sourceQualifier"] = str(source["sourceQualifier"])
        rules = source.get("cardinalityRules", ())
        if rules:
            item["cardinalityRules"] = tuple(
                {
                    "sourceTypes": tuple(sorted(source_types)),
                    "minimum": minimum,
                    "maximum": maximum,
                    "description": description,
                }
                for source_types, minimum, maximum, description in rules
            )
        result[name] = item
    return result


def _observed_node_types(data: TFData, values: dict[int, Any]) -> tuple[str, ...]:
    otype = data.node_features.get("otype", {})
    return tuple(sorted({str(otype[node]) for node in values if node in otype}))


def serialized_feature_contract(
    data: TFData,
    *,
    include_supported: bool = False,
) -> dict[str, dict[str, dict[str, Any]]]:
    """Describe the serialization-normalized TF feature contract without mutating data."""

    node_features = _node_features_with_format_dependencies(data, isolate=True)
    edge_features = _edge_features_with_api_dependencies(data, isolate=True)
    metadata = _metadata_with_serialized_features(data, node_features, edge_features)
    supported_node_descriptors = _supported_node_descriptors() if include_supported else {}
    edges = edge_feature_contracts()

    node_names = set(node_features)
    edge_names = set(edge_features)
    if include_supported:
        node_names.update(FEATURE_DESCRIPTIONS)
        node_names.update(supported_node_descriptors)
        edge_names.update(edges)

    node_contract: dict[str, dict[str, Any]] = {}
    for name in sorted(node_names):
        meta = dict(metadata.get(name, {}))
        supported_descriptor = supported_node_descriptors.get(name)
        supported_meta = supported_descriptor.get("metadata") if supported_descriptor else None
        if supported_meta:
            # Global browser help describes the converter-supported semantic
            # contract, not whichever optional features happen to occur in the
            # small fixture used to render/validate the tracked documentation.
            meta.update(supported_meta)
        meta.setdefault("valueType", "int" if name in INT_FEATURES else "str")
        meta.setdefault("description", FEATURE_DESCRIPTIONS.get(name, f"OCP/TF feature {name}"))
        meta = with_documentation_category(name, kind="node", metadata=meta)
        values = node_features.get(name, {})
        node_contract[name] = {
            "name": name,
            "kind": "node",
            "valueType": meta["valueType"],
            "description": meta["description"],
            "metadata": meta,
            "observedNodeTypes": _observed_node_types(data, values),
            "supportedNodeTypes": tuple(supported_descriptor.get("supportedNodeTypes", ())) if supported_descriptor else (),
            "serialized": name in node_features,
            "supported": True,
            "corpusDependent": name in supported_node_descriptors,
        }

    edge_contract: dict[str, dict[str, Any]] = {}
    for name in sorted(edge_names):
        meta = dict(metadata.get(name, {}))
        meta.setdefault("valueType", "str")
        meta.setdefault("description", EDGE_DESCRIPTIONS.get(name, name))
        meta = with_documentation_category(name, kind="edge", metadata=meta)
        item: dict[str, Any] = {
            "name": name,
            "kind": "edge",
            "valueType": "none",
            "edgeValues": False,
            "description": meta["description"],
            "metadata": meta,
            "serialized": name in edge_features,
            "supported": True,
            "corpusDependent": name in edges,
        }
        if name in edges:
            item.update(edges[name])
        edge_contract[name] = item

    return {"node": node_contract, "edge": edge_contract}


def _direction(item: dict[str, Any]) -> str:
    sources = ", ".join(f"`{name}`" for name in item.get("sourceTypes", ())) or "non-slot node"
    targets = ", ".join(f"`{name}`" for name in item.get("targetTypes", ())) or "node"
    return f"{sources} → {targets}"


def _render_feature_page(item: dict[str, Any]) -> str:
    lines = [
        f"# `{item['name']}`",
        "",
        f"**Kind:** {item['kind']}",
        "",
        f"**Value type:** `{item['valueType']}`",
        "",
        f"**Category:** {item['metadata']['documentationCategory']}",
        "",
        item["description"],
    ]
    if item["kind"] == "node":
        observed = tuple(item.get("observedNodeTypes", ()))
        observed_text = (
            ", ".join(f"`{node_type}`" for node_type in observed)
            if observed
            else "none in this render graph"
        )
        lines.extend(["", f"**Observed node types in render graph:** {observed_text}"])
        supported_types = tuple(item.get("supportedNodeTypes", ()))
        if supported_types:
            supported_text = ", ".join(f"`{node_type}`" for node_type in supported_types)
            lines.extend(["", f"**Supported node types:** {supported_text}"])

    if item["kind"] == "edge":
        lines.extend(
            [
                "",
                f"**Direction:** {_direction(item)}",
                "",
                f"**Cardinality:** {item.get('cardinality', 'unspecified')}",
            ]
        )
        if item.get("sourceQualifier"):
            lines.extend(["", f"**Source qualifier:** `{item['sourceQualifier']}`"])
        if item.get("technicalSupport"):
            lines.extend(
                [
                    "",
                    "This is a **technical Text-Fabric support relation**; its anchors are not scholarly containment claims.",
                ]
            )
    if item.get("corpusDependent"):
        lines.extend(
            [
                "",
                "**Supported by converter:** yes",
                "",
                "Availability is corpus-dependent; this reference does not infer absence from the documentation fixture.",
            ]
        )
    controlled = item["metadata"].get("controlledVocabularyJson")
    if controlled:
        try:
            values = json.loads(controlled)
        except (TypeError, ValueError):
            values = []
        if isinstance(values, list):
            lines.extend(["", "## Controlled vocabulary", ""])
            lines.extend(f"- `{value}`" for value in values)
    return "\n".join(lines).rstrip() + "\n"


def render_feature_docs(data: TFData) -> dict[str, str]:
    """Render deterministic help; graph-local applicability is explicitly scoped."""

    contract = serialized_feature_contract(data, include_supported=True)
    items = {**contract["node"], **contract["edge"]}
    pages = {f"{name}.md": _render_feature_page(item) for name, item in sorted(items.items())}

    grouped: dict[str, list[str]] = {category: [] for category in DOCUMENTATION_CATEGORIES}
    for name, item in sorted(items.items()):
        grouped[item["metadata"]["documentationCategory"]].append(name)
    landing = [
        "# Text-Fabric feature reference",
        "",
        "Generated from the converter's serialization-normalized supported feature and edge contracts.",
    ]
    for category in DOCUMENTATION_CATEGORIES:
        landing.extend(["", f"## {category}", ""])
        names = grouped[category]
        if names:
            landing.extend(f"- [`{name}`]({name}.md)" for name in names)
        else:
            landing.append("_No features in this contract._")
    pages["0_home.md"] = "\n".join(landing).rstrip() + "\n"
    return pages


def write_feature_docs(data: TFData, destination: str | Path) -> None:
    """Write the deterministic feature reference, replacing stale Markdown pages."""

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    pages = render_feature_docs(data)
    for path in destination.glob("*.md"):
        if path.name not in pages:
            path.unlink()
    for name, content in pages.items():
        (destination / name).write_text(content, encoding="utf-8")


def validate_feature_docs(data: TFData, destination: str | Path) -> list[str]:
    """Return deterministic drift diagnostics for an existing feature-doc tree."""

    destination = Path(destination)
    expected = render_feature_docs(data)
    failures: list[str] = []
    actual_names = {path.name for path in destination.glob("*.md")} if destination.is_dir() else set()
    for missing in sorted(set(expected) - actual_names):
        failures.append(f"missing feature documentation: {missing}")
    for stale_extra in sorted(actual_names - set(expected)):
        failures.append(f"stale extra feature documentation: {stale_extra}")
    for name in sorted(set(expected) & actual_names):
        if (destination / name).read_text(encoding="utf-8") != expected[name]:
            failures.append(f"stale feature documentation: {name}")
    return failures
