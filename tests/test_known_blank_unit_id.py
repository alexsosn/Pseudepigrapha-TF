from pathlib import Path

import pytest

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory


def _adam_eve_xml(*, version_title: str = "Latin (Mozley)", inner_div: str = "0") -> bytes:
    return f'''<book filename="AdamEve" title="Life of Adam and Eve">
  <version title="{version_title}" author="" language="Latin">
    <divisions>
      <division label="Chapter" delimiter=":"/>
      <division label="Verse"/>
    </divisions>
    <manuscripts>
      <ms abbrev="Mozley" language="Latin" show="yes"><name>Mozley</name></ms>
    </manuscripts>
    <text>
      <div number="26">
        <div number="{inner_div}">
          <unit id="" group="0" parallel="">
            <reading option="0" mss="Mozley ">alpha</reading>
          </unit>
        </div>
      </div>
    </text>
  </version>
</book>'''.encode()


def test_known_pinned_blank_unit_id_is_preserved_marked_and_audited(tmp_path: Path):
    source = tmp_path / "AdamEve.xml"
    source.write_bytes(_adam_eve_xml())

    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    data = build_tf_data(books)

    unit = next(
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "unit" and data.node_features["source_ref"][node] == "26:0"
    )
    assert unit not in data.node_features.get("unit_id", {})
    assert data.node_features["is_missing_unit_id"][unit] == 1
    assert data.node_features["is_source_anomaly"][unit] == 1

    report = build_conversion_report(tmp_path, books, data)
    assert report["status"] == "ok", report["failed_checks"]
    assert report["source"]["missing_unit_ids"] == 1
    assert report["graph"]["missing_unit_ids"] == 1
    assert report["semantic_checks"]["missing_unit_ids"] is True


@pytest.mark.parametrize(
    ("source_path", "version_title", "inner_div"),
    [
        ("Other.xml", "Latin (Mozley)", "0"),
        ("AdamEve.xml", "Other Version", "0"),
        ("AdamEve.xml", "Latin (Mozley)", "1"),
    ],
)
def test_blank_unit_id_exception_is_scoped_to_exact_pinned_identity(
    source_path: str,
    version_title: str,
    inner_div: str,
):
    with pytest.raises(InvalidSourceError, match=r"blank required identity attribute id"):
        parse_bytes(
            _adam_eve_xml(version_title=version_title, inner_div=inner_div),
            source_path=source_path,
        )
