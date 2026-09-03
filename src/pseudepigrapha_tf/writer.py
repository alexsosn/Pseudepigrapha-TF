from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

from .graph import TFData


class _FabricLike(Protocol):
    def save(self, **kwargs) -> bool: ...


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
            nodeFeatures=data.node_features,
            edgeFeatures=data.edge_features,
            metaData=data.metadata,
            location=str(output),
            module="",
            silent="deep",
        )
    )
