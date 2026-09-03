from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Protocol

from .graph import TFData


class _FabricLike(Protocol):
    def save(self, **kwargs) -> bool: ...


_FORMAT_FEATURE = re.compile(r"\{([^}:]+)(?::[^}]*)?\}")


def _node_features_with_format_dependencies(data: TFData) -> dict[str, dict[int, str | int]]:
    """Return node features including empty maps required by declared TF formats.

    Text-Fabric 13.1 compiles every ``fmt:*`` template during load and expects
    each referenced feature to have a corresponding ``.tf`` file, even if the
    particular corpus has no non-empty values for that feature. ``Fabric.save``
    only writes files for keys present in ``nodeFeatures``, so ensure those keys
    exist here rather than weakening the graph model with fake values.
    """

    node_features = {name: dict(values) for name, values in data.node_features.items()}
    for name, template in data.metadata.get("otext", {}).items():
        if not name.startswith("fmt:"):
            continue
        for feature in _FORMAT_FEATURE.findall(template):
            node_features.setdefault(feature, {})
    return node_features


def write_tf(
    data: TFData,
    output_dir: str | Path,
    *,
    fabric_factory: Callable[..., _FabricLike] | None = None,
) -> bool:
    failures = data.validate()
    if failures:
        raise ValueError("refusing to write invalid Text-Fabric data: " + "; ".join(failures))
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if fabric_factory is None:
        try:
            from tf.fabric import Fabric
        except ImportError as exc:  # pragma: no cover - environment-specific
            raise RuntimeError("Text-Fabric is required to write .tf files; install the project dependencies") from exc
        fabric_factory = Fabric
    fabric = fabric_factory(locations=[], modules=[], silent="deep")
    return bool(
        fabric.save(
            nodeFeatures=_node_features_with_format_dependencies(data),
            edgeFeatures=data.edge_features,
            metaData=data.metadata,
            location=str(output),
            module="",
            silent="deep",
        )
    )
