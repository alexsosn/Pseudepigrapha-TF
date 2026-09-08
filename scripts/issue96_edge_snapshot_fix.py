from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]


EDGE_DEPENDENCE = {
    "oslots": False,
    "parent": True,
    "reading_of": True,
    "variant_word_of": True,
    "witness": False,
    "manuscript_of": False,
    "resource_of": True,
    "translation_of": True,
    "translation_unit_of": True,
}


def patch_graph() -> None:
    path = ROOT / "src" / "pseudepigrapha_tf" / "graph.py"
    text = path.read_text(encoding="utf-8")
    for name, dependent in EDGE_DEPENDENCE.items():
        start_marker = f'    "{name}": {{\n'
        start = text.index(start_marker)
        end = text.index("    },\n", start) + len("    },\n")
        block = text[start:end]
        wanted = f'        "corpusDependent": {dependent},\n'
        if "corpusDependent" in block:
            continue
        marker = '        "technicalSupport": '
        line_start = block.index(marker)
        line_end = block.index("\n", line_start) + 1
        block = block[:line_end] + wanted + block[line_end:]
        text = text[:start] + block + text[end:]
    path.write_text(text, encoding="utf-8")


def patch_docs() -> None:
    path = ROOT / "src" / "pseudepigrapha_tf" / "feature_docs.py"
    text = path.read_text(encoding="utf-8")
    old = '            "technicalSupport": bool(source.get("technicalSupport", False)),\n            "edgeValues": False,\n'
    new = '            "technicalSupport": bool(source.get("technicalSupport", False)),\n            "corpusDependent": bool(source.get("corpusDependent", False)),\n            "edgeValues": False,\n'
    if new not in text:
        if text.count(old) != 1:
            raise RuntimeError("edge contract render patch target is not unique")
        text = text.replace(old, new, 1)
    old_condition = '    if item.get("corpusDependent") or not item.get("serialized", True):\n'
    new_condition = '    if item.get("corpusDependent"):\n'
    if new_condition not in text:
        if text.count(old_condition) != 1:
            raise RuntimeError("fixture-dependent renderer condition patch target is not unique")
        text = text.replace(old_condition, new_condition, 1)
    path.write_text(text, encoding="utf-8")


def patch_tests() -> None:
    path = ROOT / "tests" / "test_feature_contract.py"
    text = path.read_text(encoding="utf-8")
    marker = '''    assert "technical" in oslots["description"].lower()\n'''
    addition = '''    assert oslots["corpusDependent"] is False\n    assert contracts["witness"]["corpusDependent"] is False\n    assert contracts["manuscript_of"]["corpusDependent"] is False\n    assert contracts["resource_of"]["corpusDependent"] is True\n    assert contracts["translation_of"]["corpusDependent"] is True\n'''
    if addition not in text:
        if text.count(marker) != 1:
            raise RuntimeError("edge contract test patch target is not unique")
        text = text.replace(marker, marker + addition, 1)
    path.write_text(text, encoding="utf-8")


def regenerate_docs() -> None:
    from pseudepigrapha_tf import build_tf_data
    from pseudepigrapha_tf.feature_docs import write_feature_docs
    from pseudepigrapha_tf.parser import parse_file

    data = build_tf_data([parse_file(ROOT / "tests" / "fixtures" / "sample.xml")])
    write_feature_docs(data, ROOT / "docs" / "features")


if __name__ == "__main__":
    patch_graph()
    patch_docs()
    patch_tests()
    regenerate_docs()
