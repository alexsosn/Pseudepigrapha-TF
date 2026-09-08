from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count == 1:
        return text.replace(old, new)
    if new in text:
        return text
    raise RuntimeError(f"expected one patch target, found {count}: {old!r}")


def patch_sources() -> None:
    path = ROOT / "src" / "pseudepigrapha_tf" / "feature_docs.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '            "technicalSupport": bool(source.get("technicalSupport", False)),\n            "description": EDGE_DESCRIPTIONS[name],\n',
        '            "technicalSupport": bool(source.get("technicalSupport", False)),\n            "edgeValues": False,\n            "description": EDGE_DESCRIPTIONS[name],\n',
    )
    text = replace_once(
        text,
        '            "kind": "edge",\n            "valueType": meta["valueType"],\n            "description": meta["description"],\n',
        '            "kind": "edge",\n            "valueType": "none",\n            "edgeValues": False,\n            "description": meta["description"],\n',
    )
    text = replace_once(
        text,
        '    if not item.get("serialized", True):\n        lines.extend(\n            [\n                "",\n                "**Serialized in this corpus:** no",\n                "",\n                "**Supported by converter:** yes",\n            ]\n        )\n',
        '    if not item.get("serialized", True):\n        lines.extend(\n            [\n                "",\n                "**Supported by converter:** yes",\n                "",\n                "Availability is corpus-dependent; this reference does not infer absence from the documentation fixture.",\n            ]\n        )\n',
    )
    path.write_text(text, encoding="utf-8")

    tests = ROOT / "tests" / "test_feature_docs_render.py"
    text = tests.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    assert "**Serialized in this corpus:** no" in resource\n    assert "**Supported by converter:** yes" in resource\n',
        '    assert "Serialized in this corpus:" not in resource\n    assert "**Supported by converter:** yes" in resource\n    assert "Availability is corpus-dependent" in resource\n',
    )
    tests.write_text(text, encoding="utf-8")


def regenerate_docs() -> None:
    from pseudepigrapha_tf import build_tf_data
    from pseudepigrapha_tf.feature_docs import write_feature_docs
    from pseudepigrapha_tf.parser import parse_file

    data = build_tf_data([parse_file(ROOT / "tests" / "fixtures" / "sample.xml")])
    write_feature_docs(data, ROOT / "docs" / "features")


if __name__ == "__main__":
    patch_sources()
    regenerate_docs()
