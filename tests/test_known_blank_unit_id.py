import hashlib
from pathlib import Path

import pytest

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.model import Book, Div, DivisionSpec, Reading, Token, Unit, Version
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory
from pseudepigrapha_tf.source_structure import KNOWN_BLANK_UNIT_ID_SOURCES


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
          <unit id="28" group="0" parallel="">
            <reading option="0" mss="Mozley ">beta</reading>
          </unit>
        </div>
      </div>
    </text>
  </version>
</book>'''.encode()


def _case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source = tmp_path / "AdamEve.xml"
    source_bytes = _adam_eve_xml()
    monkeypatch.setitem(
        KNOWN_BLANK_UNIT_ID_SOURCES,
        ("AdamEve.xml", "AdamEve", "Latin (Mozley)", ("26", "0")),
        hashlib.sha256(source_bytes).hexdigest(),
    )
    source.write_bytes(source_bytes)
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    return books, build_tf_data(books)


def _unit(data, *, unit_id: str | None = None):
    return next(
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "unit"
        and (unit_id is None or data.node_features.get("unit_id", {}).get(node) == unit_id)
    )


def test_known_pinned_blank_unit_id_is_preserved_marked_and_audited(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    books, data = _case(tmp_path, monkeypatch)

    unit = next(
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "unit"
        and data.node_features["source_ref"][node] == "26:0"
        and node not in data.node_features.get("unit_id", {})
    )
    assert unit not in data.node_features.get("unit_id", {})
    assert data.node_features["is_missing_unit_id"][unit] == 1
    assert data.node_features["is_source_anomaly"][unit] == 1

    report = build_conversion_report(tmp_path, books, data)
    assert report["status"] == "ok", report["failed_checks"]
    assert report["source"]["missing_unit_ids"] == 1
    assert report["graph"]["missing_unit_ids"] == 1
    assert report["semantic_checks"]["missing_unit_ids"] is True


@pytest.mark.parametrize("feature", ["is_missing_unit_id", "is_source_anomaly"])
def test_missing_unit_id_audit_rejects_missing_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    feature: str,
):
    books, data = _case(tmp_path, monkeypatch)
    missing = next(
        node
        for node in data.node_features["is_missing_unit_id"]
        if data.node_features["is_missing_unit_id"][node] == 1
    )
    data.node_features[feature].pop(missing)

    report = build_conversion_report(tmp_path, books, data)
    assert report["status"] == "failed"
    assert report["semantic_checks"]["missing_unit_ids"] is False


def test_missing_unit_id_audit_rejects_spurious_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    books, data = _case(tmp_path, monkeypatch)
    regular = _unit(data, unit_id="28")
    data.node_features.setdefault("is_missing_unit_id", {})[regular] = 1
    data.node_features.setdefault("is_source_anomaly", {})[regular] = 1

    report = build_conversion_report(tmp_path, books, data)
    assert report["status"] == "failed"
    assert report["semantic_checks"]["missing_unit_ids"] is False


def test_direct_model_cannot_spoof_known_blank_unit_with_source_path():
    reading = Reading(
        option="0",
        witnesses=(),
        mss_raw="",
        linebreak="",
        indent="",
        text="alpha",
        content_xml="alpha",
        tokens=(Token("alpha"),),
    )
    missing = Unit(
        unit_id="",
        group="0",
        parallel="",
        linebreak="",
        readings=(reading,),
    )
    version = Version(
        title="Latin (Mozley)",
        author="",
        language="Latin",
        fragment="",
        divisions=(DivisionSpec("Chapter", ":"), DivisionSpec("Verse")),
        resources=(),
        manuscripts=(),
        divs=(Div("26", "", (Div("0", "", (missing,)),)),),
    )
    book = Book(
        filename="AdamEve",
        title="Life of Adam and Eve",
        text_structure="",
        versions=(version,),
        source_path="AdamEve.xml",
    )

    with pytest.raises(ValueError, match=r"blank unit id"):
        build_tf_data([book])


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
