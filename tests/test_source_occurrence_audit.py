from __future__ import annotations

from pathlib import Path

from pseudepigrapha_tf import Apparatus
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory
from pseudepigrapha_tf.writer import write_tf


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


def _duplicate_units(data):
    otype = data.node_features["otype"]
    source_ref = data.node_features["source_ref"]
    unit_id = data.node_features["unit_id"]
    unit_index = data.node_features["unit_index"]
    return sorted(
        (
            node
            for node, node_type in otype.items()
            if node_type == "unit"
            and source_ref.get(node) == "1:1"
            and unit_id.get(node) == "7"
        ),
        key=lambda node: unit_index[node],
    )


def _duplicate_readings(data, first_unit, second_unit):
    reading_of = data.edge_features["reading_of"]
    first_reading = next(
        reading for reading, targets in reading_of.items() if targets == {first_unit}
    )
    second_reading = next(
        reading for reading, targets in reading_of.items() if targets == {second_unit}
    )
    return first_reading, second_reading


def test_conversion_report_rejects_swapped_duplicate_source_unit_reading_owners(
    tmp_path: Path,
) -> None:
    books = _source(tmp_path)
    data = build_tf_data(books)

    baseline = build_conversion_report(tmp_path, books, data)
    assert baseline["status"] == "ok", baseline["failed_checks"]

    duplicates = _duplicate_units(data)
    assert len(duplicates) == 2
    first_unit, second_unit = duplicates

    reading_text = data.node_features["reading_text"]
    reading_of = data.edge_features["reading_of"]
    first_reading, second_reading = _duplicate_readings(data, first_unit, second_unit)
    assert reading_text[first_reading] == "alpha"
    assert reading_text[second_reading] == "beta"

    # Preserve every stamped source identity/payload while reversing only the
    # relation that the researcher-facing apparatus API uses for unit ownership.
    reading_of[first_reading] = {second_unit}
    reading_of[second_reading] = {first_unit}

    report = build_conversion_report(tmp_path, books, data)

    assert report["semantic_checks"]["reading_ownership"] is False
    assert "reading_ownership" in report["failed_checks"]


def test_reading_ownership_rejects_coordinated_owner_and_support_swap(
    tmp_path: Path,
) -> None:
    """Adversarial review: oslots alone must not define occurrence identity."""

    books = _source(tmp_path)
    data = build_tf_data(books)
    first_unit, second_unit = _duplicate_units(data)
    first_reading, second_reading = _duplicate_readings(data, first_unit, second_unit)
    reading_of = data.edge_features["reading_of"]
    oslots = data.edge_features["oslots"]

    # A future builder regression could conceivably carry both the wrong owner
    # key and the wrong unit support forward together. That must still fail the
    # ownership-specific semantic check rather than depending on reconstruction.
    reading_of[first_reading] = {second_unit}
    reading_of[second_reading] = {first_unit}
    oslots[first_reading], oslots[second_reading] = (
        set(oslots[second_reading]),
        set(oslots[first_reading]),
    )

    report = build_conversion_report(tmp_path, books, data)

    assert report["semantic_checks"]["reading_ownership"] is False


def test_duplicate_source_units_roundtrip_with_correct_apparatus_ownership(
    tmp_path: Path,
) -> None:
    from tf.fabric import Fabric

    books = _source(tmp_path)
    data = build_tf_data(books)
    output = tmp_path / "tf"
    assert write_tf(data, output)

    tf = Fabric(locations=[str(output)], modules=[""], silent="deep")
    api = tf.load(
        "unit_id source_ref unit_index reading_text reading_of",
        silent="deep",
    )
    assert api is not None

    units = sorted(
        (
            unit
            for unit in api.F.otype.s("unit")
            if api.F.source_ref.v(unit) == "1:1" and api.F.unit_id.v(unit) == "7"
        ),
        key=lambda unit: api.F.unit_index.v(unit),
    )
    assert len(units) == 2
    assert [api.F.unit_id.v(unit) for unit in units] == ["7", "7"]
    assert [api.F.source_ref.v(unit) for unit in units] == ["1:1", "1:1"]

    apparatus = Apparatus(api)
    first_readings = apparatus.unit_readings(units[0])
    second_readings = apparatus.unit_readings(units[1])
    assert [apparatus.reading_text(reading) for reading in first_readings] == ["alpha"]
    assert [apparatus.reading_text(reading) for reading in second_readings] == ["beta"]
