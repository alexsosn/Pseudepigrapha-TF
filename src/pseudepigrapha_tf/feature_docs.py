from __future__ import annotations

from typing import Any

from .graph import EDGE_DESCRIPTIONS, EDGE_FEATURE_CONTRACTS, FEATURE_DESCRIPTIONS, INT_FEATURES, TFData
from .writer import (
    _edge_features_with_api_dependencies,
    _metadata_with_serialized_features,
    _node_features_with_format_dependencies,
)


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
    """Describe the serialization-normalized TF feature contract without mutating data.

    ``serialized`` distinguishes features that would receive a ``.tf``
    file for this graph from supported optional relations/features that
    are documented through the converter's canonical contracts.
    """

    node_features = _node_features_with_format_dependencies(data, isolate=True)
    edge_features = _edge_features_with_api_dependencies(data, isolate=True)
    metadata = _metadata_with_serialized_features(data, node_features, edge_features)
    edges = edge_feature_contracts()

    node_names = set(node_features)
    edge_names = set(edge_features)
    if include_supported:
        node_names.update(FEATURE_DESCRIPTIONS)
        edge_names.update(edges)

    node_contract: dict[str, dict[str, Any]] = {}
    for name in sorted(node_names):
        meta = dict(metadata.get(name, {}))
        meta.setdefault("valueType", "int" if name in INT_FEATURES else "str")
        meta.setdefault("description", FEATURE_DESCRIPTIONS.get(name, f"OCP/TF feature {name}"))
        values = node_features.get(name, {})
        node_contract[name] = {
            "name": name,
            "kind": "node",
            "valueType": meta["valueType"],
            "description": meta["description"],
            "metadata": meta,
            "observedNodeTypes": _observed_node_types(data, values),
            "serialized": name in node_features,
            "supported": True,
        }

    edge_contract: dict[str, dict[str, Any]] = {}
    for name in sorted(edge_names):
        meta = dict(metadata.get(name, {}))
        meta.setdefault("valueType", "str")
        meta.setdefault("description", EDGE_DESCRIPTIONS.get(name, name))
        item: dict[str, Any] = {
            "name": name,
            "kind": "edge",
            "valueType": meta["valueType"],
            "description": meta["description"],
            "metadata": meta,
            "serialized": name in edge_features,
            "supported": True,
        }
        if name in edges:
            item.update(edges[name])
        edge_contract[name] = item

    return {"node": node_contract, "edge": edge_contract}
