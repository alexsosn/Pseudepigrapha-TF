from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_exact(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} matches, found {count}")
    return text.replace(old, new)


conversion_path = ROOT / "src" / "pseudepigrapha_tf" / "conversion.py"
conversion = conversion_path.read_text(encoding="utf-8")
conversion = replace_exact(
    conversion,
    '''    _validate_generated_alignment(data)\n\n    data.metadata["otext"]["fmt:version_metadata-default"] = "{version_title}"\n''',
    '''    _validate_generated_alignment(data)\n\n    if any(\n        value == "generated_translation"\n        for value in data.node_features.get("version_kind", {}).values()\n    ):\n        # Generic TF metadata is copied into every serialized feature's metadata.\n        # This corpus capability marker therefore remains discoverable through\n        # the always-loaded otype feature even when provenance features are not\n        # part of a researcher's selective load.\n        data.metadata[""]["generatedTranslationLayer"] = "1"\n\n    data.metadata["otext"]["fmt:version_metadata-default"] = "{version_title}"\n''',
    1,
    "generated corpus capability marker",
)
conversion_path.write_text(conversion, encoding="utf-8")

apparatus_path = ROOT / "src" / "pseudepigrapha_tf" / "apparatus.py"
apparatus = apparatus_path.read_text(encoding="utf-8")
apparatus = replace_exact(
    apparatus,
    '''    def _require_edge(self, name: str):\n        edge = getattr(self.api.E, name, None)\n        if edge is None:\n            raise ValueError(f"edge feature {name!r} must be loaded for this Apparatus operation")\n        return edge\n\n''',
    '''    def _require_edge(self, name: str):\n        edge = getattr(self.api.E, name, None)\n        if edge is None:\n            raise ValueError(f"edge feature {name!r} must be loaded for this Apparatus operation")\n        return edge\n\n    def _generated_layer_declared(self) -> bool:\n        """Detect generated-capable corpora without requiring optional features to be loaded."""\n\n        tf = getattr(self.api, "TF", None)\n        features = getattr(tf, "features", None)\n        if not isinstance(features, dict):\n            return False\n        otype_info = features.get("otype")\n        metadata = getattr(otype_info, "metaData", None) if otype_info is not None else None\n        return isinstance(metadata, dict) and str(metadata.get("generatedTranslationLayer", "")) == "1"\n\n    def _version_kind_feature(self):\n        if self._generated_layer_declared():\n            return self._require_feature("version_kind")\n        return getattr(self.api.F, "version_kind", None)\n\n    def _synthetic_witness_feature(self):\n        if self._generated_layer_declared():\n            return self._require_feature("synthetic_witness")\n        return getattr(self.api.F, "synthetic_witness", None)\n\n    def _reject_generated_unit(self, unit: int) -> None:\n        if not self._generated_layer_declared():\n            return\n        version_kind = self._require_feature("version_kind")\n        if self._required_feature_value(version_kind, "version_kind", unit) == "generated_translation":\n            raise ValueError(\n                f"unit {unit} belongs to a generated translation; use Translations for aligned text, "\n                "not historical apparatus semantics"\n            )\n\n    def _reject_synthetic_manuscript(self, manuscript: int) -> None:\n        if not self._generated_layer_declared():\n            return\n        synthetic_witness = self._require_feature("synthetic_witness")\n        if synthetic_witness.v(manuscript) == 1:\n            raise ValueError(\n                f"manuscript {manuscript} is a synthetic translation provenance witness, "\n                "not a historical manuscript"\n            )\n\n''',
    1,
    "apparatus capability helpers",
)
apparatus = replace_exact(
    apparatus,
    '''    def _is_generated_book(self, book_node: int) -> bool:\n        version_kind = getattr(self.api.F, "version_kind", None)\n        return version_kind is not None and version_kind.v(book_node) == "generated_translation"\n''',
    '''    def _is_generated_book(self, book_node: int) -> bool:\n        version_kind = self._version_kind_feature()\n        return version_kind is not None and version_kind.v(book_node) == "generated_translation"\n''',
    1,
    "generated book guard",
)
apparatus = replace_exact(
    apparatus,
    '        synthetic_witness = getattr(self.api.F, "synthetic_witness", None)\n',
    '        synthetic_witness = self._synthetic_witness_feature()\n',
    3,
    "synthetic witness conditional loads",
)
apparatus = replace_exact(
    apparatus,
    '''    def witness_reading(self, unit: int, manuscript: int) -> int | None:\n        witness = self._require_edge("witness")\n''',
    '''    def witness_reading(self, unit: int, manuscript: int) -> int | None:\n        self._reject_generated_unit(unit)\n        self._reject_synthetic_manuscript(manuscript)\n        witness = self._require_edge("witness")\n''',
    1,
    "direct witness reading guard",
)
apparatus = replace_exact(
    apparatus,
    '''    def witness_text(self, manuscript: int, units: Iterable[int] | None = None) -> str:\n        if units is None:\n''',
    '''    def witness_text(self, manuscript: int, units: Iterable[int] | None = None) -> str:\n        self._reject_synthetic_manuscript(manuscript)\n        if units is None:\n''',
    1,
    "direct witness text guard",
)
apparatus = replace_exact(
    apparatus,
    '''    def apparatus(self, unit: int) -> tuple[dict[str, object], ...]:\n        is_primary = self._require_feature("is_primary")\n''',
    '''    def apparatus(self, unit: int) -> tuple[dict[str, object], ...]:\n        self._reject_generated_unit(unit)\n        is_primary = self._require_feature("is_primary")\n''',
    1,
    "direct apparatus unit guard",
)
apparatus = replace_exact(
    apparatus,
    '        version_kind = getattr(self.api.F, "version_kind", None)\n\n        textual_versions = tuple(\n',
    '        version_kind = self._version_kind_feature()\n\n        textual_versions = tuple(\n',
    1,
    "work passage conditional version load",
)
apparatus_path.write_text(apparatus, encoding="utf-8")
