from __future__ import annotations

import re
import shutil
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp
from typing import Callable, Protocol

from .graph import EDGE_DESCRIPTIONS, INT_FEATURES, TFData


class _FabricLike(Protocol):
    def save(self, **kwargs) -> bool: ...


class _TFInstallRollbackError(RuntimeError):
    """Installation failed and the previous TF set could not be fully restored."""

    def __init__(
        self,
        install_error: BaseException,
        rollback_error: BaseException,
        backup: Path,
    ) -> None:
        super().__init__(
            "Text-Fabric installation failed "
            f"({install_error}); rollback also failed ({rollback_error}); "
            f"recoverable backup retained at {backup}"
        )
        self.install_error = install_error
        self.rollback_error = rollback_error
        self.backup = backup


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


def _rollback_tf_features(output: Path, backup: Path, original_names: frozenset[str]) -> None:
    """Restore the pre-install TF set while leaving non-TF sidecars untouched."""

    # New-only files have no counterpart in the previous generation. Common
    # names are overwritten below from backup, and untouched old files remain
    # in place when failure happened part-way through the backup phase.
    for path in sorted(output.glob("*.tf"), key=lambda item: item.name):
        if path.name not in original_names:
            path.unlink()
    for path in sorted(backup.glob("*.tf"), key=lambda item: item.name):
        path.replace(output / path.name)


def _install_staged_tf_features(stage: Path, output: Path) -> None:
    """Install one staged TF generation and restore the previous set on failure.

    The stage and backup are siblings of ``output``, so normal ``Path.replace``
    operations stay on one filesystem. This guarantees recovery after a failed
    transaction; it does not claim lock-free atomic visibility to concurrent
    readers during the finite sequence of renames.
    """

    staged = tuple(sorted(stage.glob("*.tf"), key=lambda item: item.name))
    existing = tuple(sorted(output.glob("*.tf"), key=lambda item: item.name))
    original_names = frozenset(path.name for path in existing)
    backup = Path(mkdtemp(prefix=".pseudepigrapha-tf-backup-", dir=output.parent))

    try:
        for path in existing:
            path.replace(backup / path.name)
        for path in staged:
            path.replace(output / path.name)
    except BaseException as install_error:
        try:
            _rollback_tf_features(output, backup, original_names)
        except BaseException as rollback_error:
            raise _TFInstallRollbackError(
                install_error,
                rollback_error,
                backup,
            ) from rollback_error
        else:
            # A successful rollback moves every backed-up TF file back out, so
            # only the empty directory remains. Preserve the original install
            # exception even if housekeeping of that empty directory fails.
            try:
                backup.rmdir()
            except OSError as cleanup_error:
                warnings.warn(
                    "previous TF set was restored, but empty backup cleanup "
                    f"failed at {backup}: {cleanup_error}",
                    RuntimeWarning,
                    stacklevel=2,
                )
            raise
    else:
        try:
            shutil.rmtree(backup)
        except Exception as cleanup_error:
            raise RuntimeError(
                "Text-Fabric features were installed successfully, but the old "
                f"backup could not be removed and remains at {backup}: {cleanup_error}"
            ) from cleanup_error


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
    uses_standard_fabric = fabric_factory is None
    isolate_payload = not uses_standard_fabric
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

    def save(location: Path) -> bool:
        return bool(
            fabric.save(
                nodeFeatures=node_features,
                edgeFeatures=edge_features,
                metaData=metadata,
                location=str(location),
                module="",
                silent="deep",
            )
        )

    if not uses_standard_fabric:
        return save(output)

    # Text-Fabric writes support files in addition to the supplied feature maps
    # (for example ``__characters__.tf``). Let it produce the complete current
    # artifact set in isolation, then reconcile only ``*.tf`` into the output.
    # A false/raising save leaves the previously generated corpus untouched.
    with TemporaryDirectory(prefix=".pseudepigrapha-tf-", dir=output.parent) as stage_dir:
        stage = Path(stage_dir)
        if not save(stage):
            return False
        _install_staged_tf_features(stage, output)
    return True


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
