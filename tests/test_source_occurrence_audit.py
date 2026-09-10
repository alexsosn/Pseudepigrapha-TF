from __future__ import annotations

from pathlib import Path

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory


XML = '''<?xml version="1.0"?>
<book filename="DuplicateUnits" title="Duplicate Units">
  <version title="Greek" author="Editor" language="Greek">
    <divisions><division label="Chapter" delimiter=":"/><division label="Verse"/></divisions>
    <manuscripts><ms abbrev="G" language="Greek" show="yes"><name>G</name></ms></manuscripts>
    <text>
      <div number="1"><div number="1">
        <unit id="7"><reading option="0" mss="G ">alpha</reading></unit>
        <unit id="7"><reading option="0" mss="G ">beta</reading></unit>
      </div></div>
    </text>
  </version>
</book>
'''


def _source(tmp_path: Path):
    path = tmp_path / "DuplicateUnits.xml"
    path.write_text(XML, encoding="utf-8")
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    return books


def test_conversion_report_rejects_swapped_duplicate_source_unit_reading_owners(
    tmp_path: Path,
) -> None:
    books = _source(tmp_path)
    data = build_tf_data(books)

    baseline = build_conversion_report(tmp_path, books, data)
    assert baseline["status"] == "ok", baseline["failed_checks"]

    otype = data.node_features["otype"]
    source_ref = data.node_features["source_ref"]
    unit_id = data.node_features["unit_id"]
    unit_index = data.node_features["unit_index"]
    reading_text = data.node_features["reading_text"]
    reading_of = data.edge_features["reading_of"]

    duplicates = sorted(
        (
            node
            for node, node_type in otype.items()
            if node_type == "unit"
            and source_ref.get(node) == "1:1"
            and unit_id.get(node) == "7"
        ),
        key=lambda node: unit_index[node],
    )
    assert len(duplicates) == 2
    first_unit, second_unit = duplicates

    first_reading = next(
        reading for reading, targets in reading_of.items() if targets == {first_unit}
    )
    second_reading = next(
        reading for reading, targets in reading_of.items() if targets == {second_unit}
    )
    assert reading_text[first_reading] == "alpha"
    assert reading_text[second_reading] == "beta"

    # Preserve every stamped source identity/payload while reversing only the
    # relation that the researcher-facing apparatus API uses for unit ownership.
    reading_of[first_reading] = {second_unit}
    reading_of[second_reading] = {first_unit}

    report = build_conversion_report(tmp_path, books, data)

    assert report["semantic_checks"]["reading_ownership"] is False
    assert "reading_ownership" in report["failed_checks"]
