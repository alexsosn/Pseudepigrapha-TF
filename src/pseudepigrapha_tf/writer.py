from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Protocol

from .graph import EDGE_DESCRIPTIONS, INT_FEATURES, TFData


class _FabricLike(Protocol):
    def save(self, **kwargs) -> bool: ...


_FORMAT_FEATURE = re.compile(r"\{([^}:]+)(?::[^}]*)?\}")
_ALWAYS_SERIALIZED_NODE_FEATURES = frozenset({"undefined_manuscript"})
_ALWAYS_SERIALIZED_EDGE_FEATURES = frozenset({"witness", "manuscript_of"})


def _node_features_with_format_dependencies(
    data: TFData,
    *,
    isolate: bool = True,
) -> dict[str, dict[int, str | int]]:
    """Return node features including empty maps required by TF/API contracts.

    Text-Fabric 13.1 compiles every ``fmt:*`` template during load and expects
    each referenced feature to have a corresponding ``.tf`` file, even if the
    particular corpus has no non-empty values for that feature. ``Fabric.save``
    only writes files for keys present in ``nodeFeatures``, so ensure those keys
    exist here rather than weakening the graph model with fake values.

    The high-level Apparatus API also needs ``undefined_manuscript`` to exist in
    every serialized corpus so it can distinguish an explicitly synthesized
    citation-only witness from a declared upstream manuscript without guessing
    when the corpus happens to contain no synthesized witnesses.
    """

    node_features = (
        {name: dict(values) for name, values in data.node_features.items()}
        if isolate
        else dict(data.node_features)
    )
    for name, template in data.metadata.get("otext", {}).items():
        if not name.startswith("fmt:"):
            continue
        for feature in _FORMAT_FEATURE.findall(template):
            node_features.setdefault(feature, {})
    for feature in _ALWAYS_SERIALIZED_NODE_FEATURES:
        node_features.setdefault(feature, {})
    return node_features


def _edge_features_with_api_dependencies(
    data: TFData,
    *,
    isolate: bool = True,
) -> dict[str, dict[int, set[int]]]:
    """Return edge features plus stable core API relations for serialization."""

    edge_features = (
        {
            name: {source: set(targets) for source, targets in values.items()}
            for name, values in data.edge_features.items()
        }
        if isolate
        else dict(data.edge_features)
    )
    for feature in _ALWAYS_SERIALIZED_EDGE_FEATURES:
        edge_features.setdefault(feature, {})
    return edge_features


def _metadata_with_serialized_features(
    data: TFData,
    node_features: dict[str, dict[int, str | int]],
    edge_features: dict[str, dict[int, set[int]]],
) -> dict[str, dict[str, str]]:
    """Ensure every serialized node and edge feature has valid TF metadata."""

    metadata = {name: dict(values) for name, values in data.metadata.items()}
    for feature in node_features:
        metadata.setdefault(
            feature,
            {
                "valueType": "int" if feature in INT_FEATURES else "str",
                "description": f"OCP/TF feature {feature}",
            },
        )
    for feature in edge_features:
        metadata.setdefault(
            feature,
            {
                "valueType": "str",
                "description": EDGE_DESCRIPTIONS.get(feature, feature),
            },
        )
    return metadata


def _serialize_tf(
    data: TFData,
    output_dir: str | Path,
    *,
    fabric_factory: Callable[..., _FabricLike] | None = None,
) -> bool:
    """Serialize data that has already crossed the caller's validation boundary."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # The built-in Text-Fabric serializer treats feature mappings as read-only,
    # so its normal CLI path can reuse the graph payload. Explicit custom
    # factories remain an untrusted boundary and receive defensive deep copies.
    isolate_payload = fabric_factory is not None
    if fabric_factory is None:
        try:
            from tf.fabric import Fabric
        except ImportError as exc:  # pragma: no cover - environment-specific
            raise RuntimeError("Text-Fabric is required to write .tf files; install the project dependencies") from exc
        fabric_factory = Fabric

    node_features = _node_features_with_format_dependencies(data, isolate=isolate_payload)
    edge_features = _edge_features_with_api_dependencies(data, isolate=isolate_payload)
    metadata = _metadata_with_serialized_features(data, node_features, edge_features)
    fabric = fabric_factory(locations=[], modules=[], silent="deep")
    return bool(
        fabric.save(
            nodeFeatures=node_features,
            edgeFeatures=edge_features,
            metaData=metadata,
            location=str(output),
            module="",
            silent="deep",
        )
    )


def _write_prevalidated_tf(data: TFData, output_dir: str | Path) -> bool:
    """Serialize the CLI's freshly generated and already validated graph."""

    return _serialize_tf(data, output_dir)


def write_tf(
    data: TFData,
    output_dir: str | Path,
    *,
    fabric_factory: Callable[..., _FabricLike] | None = None,
) -> bool:
    failures = data.validate()
    if failures:
        raise ValueError("refusing to write invalid Text-Fabric data: " + "; ".join(failures))
    return _serialize_tf(data, output_dir, fabric_factory=fabric_factory)
