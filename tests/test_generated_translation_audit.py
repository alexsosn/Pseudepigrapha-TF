from __future__ import annotations

from pathlib import Path

from pseudepigrapha_tf import audit
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory


XML = '''<?xml version="1.0"?>
<book filename="Demo" title="Demo">
  <version title="Greek" author="Editor" language="Greek">
    <divisions><division label="Chapter" delimiter=":"/><division label="Verse"/></divisions>
    <manuscripts><ms abbrev="G" language="Greek" show="yes"><name>G</name></ms></manuscripts>
    <text>
      <div number="1"><div number="1">
        <unit id="7"><reading option="0" mss="G ">alpha</reading></unit>
        <unit id="7"><reading option="0" mss="G ">beta</reading></unit>
      </div></div>
      <div number="2"><div number="1">
        <unit id="8"><reading option="0" mss="G ">gamma</reading></unit>
      </div></div>
    </text>
  </version>
  <version title="Greek (French)" author="Editor" language="French">
    <divisions><division label="Chapter" delimiter=":"/><division label="Verse"/></divisions>
    <manuscripts><ms abbrev="OCP-Trans" language="French" show="yes"><name>OCP French Translation</name></ms></manuscripts>
    <text>
      <div number="2"><div number="1">
        <unit id="fr_8"><reading option="0" mss="OCP-Trans ">gamma-fr</reading></unit>
      </div></div>
      <div number="1"><div number="1">
        <unit id="fr_7"><reading option="0" mss="OCP-Trans ">alpha-fr</reading></unit>
        <unit id="fr_7"><reading option="0" mss="OCP-Trans ">beta-fr</reading></unit>
      </div></div>
    </text>
  </version>
</book>
'''


def _source(tmp_path: Path):
    path = tmp_path / "Demo.xml"
    path.write_text(XML, encoding="utf-8")
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    return books


def test_raw_audit_independently_classifies_and_maps_generated_translation(tmp_path: Path) -> None:
    _source(tmp_path)

    raw = audit._raw_inventory(tmp_path)

    assert raw["excluded_generated_translation_versions"] == []
    assert raw["generated_translations"] == [
        {
            "ocp_book": "Demo",
            "version_title": "Greek (French)",
            "language": "French",
            "source_file": "Demo.xml",
            "marker": "OCP-Trans",
            "source_version_title": "Greek",
            "source_version_language": "Greek",
            "unit_count": 3,
            "aligned_unit_count": 3,
        }
    ]
    assert {record["version_kind"] for record in raw["versions"]} == {
        "source",
        "generated_translation",
    }


def test_conversion_report_proves_generated_text_and_alignment_from_raw_xml(tmp_path: Path) -> None:
    books = _source(tmp_path)
    data = build_tf_data(books, upstream_commit="pinned-ocp")

    report = build_conversion_report(tmp_path, books, data)

    assert report["status"] == "ok", report["failed_checks"]
    assert report["semantic_checks"]["generated_translation_alignment"] is True
    assert report["semantic_checks"]["generated_translation_provenance"] is True
    assert report["source"]["generated_translation_versions"] == 1
    assert report["source"]["generated_translation_units"] == 3
    assert report["graph"]["generated_translation_versions"] == 1
    assert report["graph"]["generated_translation_units"] == 3
    assert report["graph"]["translation_of_edges"] == 1
    assert report["graph"]["translation_unit_of_edges"] == 3
    assert report["provenance"]["upstream_commit"] == "pinned-ocp"
    assert report["generated_translations"]["by_language"] == {"French": {"versions": 1, "units": 3}}
    assert report["diagnostics"]["generated_translation_mapping_failures"] == []
