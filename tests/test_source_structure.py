from pathlib import Path

import pytest

from pseudepigrapha_tf import audit
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes, parse_file
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory

FIXTURES = Path(__file__).parent / "fixtures"


def _modern_xml(*, version_extra="", division_extra="", div_extra="", unit_extra="", reading_extra="") -> bytes:
    return f'''<book filename="Drift" title="Schema drift" textStructure="criticalApparatus">
  <version title="Greek" author="Anonymous" language="Greek">
    {version_extra}
    <divisions><division label="Chapter" delimiter=":" >{division_extra}</division></divisions>
    <manuscripts><ms abbrev="A" language="Greek" show="yes"><name>Witness A</name></ms></manuscripts>
    <text><div number="1">{div_extra}<unit id="1">{unit_extra}<reading option="0" mss="A ">alpha{reading_extra}</reading></unit></div></text>
  </version>
</book>'''.encode()


def _case(tmp_path, fixture_name):
    source = FIXTURES / fixture_name
    (tmp_path / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    data = build_tf_data(books)
    baseline = build_conversion_report(tmp_path, books, data)
    assert baseline["status"] == "ok", baseline["failed_checks"]
    return books, data


def _node(data, kind, feature=None, value=None):
    return next(
        node
        for node, node_kind in data.node_features["otype"].items()
        if node_kind == kind
        and (feature is None or data.node_features.get(feature, {}).get(node) == value)
    )


@pytest.mark.parametrize(
    ("parent", "kwargs"),
    [
        ("version", {"version_extra": "<future/>"}),
        ("division", {"division_extra": "<future>metadata</future>"}),
        ("div", {"div_extra": "<future><unit id='lost'/></future>"}),
        ("unit", {"unit_extra": "<future/>"}),
        ("reading", {"reading_extra": "<future>beta</future>"}),
    ],
)
def test_modern_parser_rejects_unsupported_direct_children(parent, kwargs):
    with pytest.raises(InvalidSourceError, match=rf"unsupported <future> child of <{parent}>"):
        parse_bytes(_modern_xml(**kwargs), source_path="drift.xml")


def test_raw_audit_rejects_same_schema_drift_instead_of_inventorying_it(tmp_path):
    (tmp_path / "drift.xml").write_bytes(_modern_xml(div_extra="<future/>"))

    with pytest.raises(InvalidSourceError, match=r"unsupported <future> child of <div>"):
        audit._raw_inventory(tmp_path)


def test_upstream_elipsis_extension_is_preserved_in_model_and_graph():
    book = parse_file(FIXTURES / "ellipsis.xml")
    marker = book.versions[0].divs[0].items[1]
    assert marker.__class__.__name__ == "Ellipsis"
    assert marker.source_tag == "elipsis"
    assert marker.text == "lost passage"

    data = build_tf_data([book])
    markers = [n for n, kind in data.node_features["otype"].items() if kind == "ellipsis"]
    assert len(markers) == 1
    node = markers[0]
    assert data.node_features["source_tag"][node] == "elipsis"
    assert data.node_features["ellipsis_text"][node] == "lost passage"
    assert data.node_features["source_ref"][node] == "1"
    assert data.node_features["source_child_index"][node] == 2
    assert len(data.edge_features["oslots"][node]) == 1

    parent = next(
        n for n, kind in data.node_features["otype"].items()
        if kind == "div" and data.node_features["source_ref"][n] == "1"
    )
    assert data.edge_features["parent"][node] == {parent}
    assert data.max_slot == 2


def test_conversion_report_audits_upstream_elipsis_extension(tmp_path):
    books, data = _case(tmp_path, "ellipsis.xml")
    report = build_conversion_report(tmp_path, books, data)
    assert report["source"]["ellipses"] == report["graph"]["ellipses"] == 1
    assert report["semantic_checks"]["ellipses"] is True
    assert report["semantic_checks"]["ellipsis_anchors"] is True


@pytest.mark.parametrize("mutation", ["payload", "parent", "anchor"])
def test_ellipsis_audit_rejects_graph_corruption(tmp_path, mutation):
    books, data = _case(tmp_path, "ellipsis.xml")
    node = _node(data, "ellipsis")

    if mutation == "payload":
        data.node_features["ellipsis_text"][node] = "corrupt"
        expected = "ellipses"
    elif mutation == "parent":
        wrong_parent = _node(data, "div", "source_ref", "1:1")
        data.edge_features["parent"][node] = {wrong_parent}
        expected = "ellipses"
    else:
        data.edge_features["oslots"][node] = {1, 2}
        expected = "ellipsis_anchors"

    report = build_conversion_report(tmp_path, books, data)
    assert report["status"] == "failed"
    assert report["semantic_checks"][expected] is False


def test_direct_div_reading_is_preserved_without_inventing_a_unit():
    book = parse_file(FIXTURES / "orphan_reading.xml")
    parent_div = book.versions[0].divs[0].children[0]
    orphan = parent_div.items[1]
    assert orphan.__class__.__name__ == "OrphanReading"
    assert orphan.source_tag == "reading"
    assert orphan.reading.option == "2"
    assert orphan.reading.witnesses == ("B", "X")
    assert orphan.reading.text == "orphan beta"
    assert "<w lex=\"x\" morph=\"N\">beta</w>" in orphan.reading.content_xml

    data = build_tf_data([book])
    nodes = [n for n, kind in data.node_features["otype"].items() if kind == "orphan_reading"]
    assert len(nodes) == 1
    node = nodes[0]
    assert data.node_features["source_tag"][node] == "reading"
    assert data.node_features["source_ref"][node] == "1:1"
    assert data.node_features["source_child_index"][node] == 2
    assert data.node_features["reading_option_source"][node] == "2"
    assert data.node_features["reading_text"][node] == "orphan beta"
    assert data.node_features["mss"][node] == "B X"
    assert data.node_features["linebreak"][node] == "following"
    assert data.node_features["indent"][node] == "1"
    assert node not in data.edge_features.get("reading_of", {})
    assert len(data.edge_features["oslots"][node]) == 1

    witnesses = {
        data.node_features["ms_abbrev"][target]: target
        for target in data.edge_features["witness"][node]
    }
    assert set(witnesses) == {"B", "X"}
    assert data.node_features.get("undefined_manuscript", {}).get(witnesses["B"], 0) == 0
    assert data.node_features["undefined_manuscript"][witnesses["X"]] == 1

    parent = _node(data, "div", "source_ref", "1:1")
    owner = _node(data, "book")
    assert data.edge_features["parent"][node] == {parent}
    assert data.edge_features["manuscript_of"][witnesses["X"]] == {owner}
    assert data.node_features["version_id"][witnesses["X"]] == data.node_features["version_id"][node]
    assert data.max_slot == 2


def test_conversion_report_audits_direct_div_reading_anomaly(tmp_path):
    books, data = _case(tmp_path, "orphan_reading.xml")
    report = build_conversion_report(tmp_path, books, data)
    assert report["source"]["orphan_readings"] == report["graph"]["orphan_readings"] == 1
    assert report["semantic_checks"]["orphan_readings"] is True
    assert report["semantic_checks"]["orphan_reading_anchors"] is True
    assert report["semantic_checks"]["orphan_witness_ownership"] is True


@pytest.mark.parametrize("mutation", ["payload", "parent", "anchor", "delete_witness", "retarget_witness"])
def test_orphan_reading_audit_rejects_graph_corruption(tmp_path, mutation):
    books, data = _case(tmp_path, "orphan_reading.xml")
    node = _node(data, "orphan_reading")

    if mutation == "payload":
        data.node_features["reading_text"][node] = "corrupt"
        expected = "orphan_readings"
    elif mutation == "parent":
        wrong_parent = _node(data, "div", "source_ref", "1")
        data.edge_features["parent"][node] = {wrong_parent}
        expected = "orphan_readings"
    elif mutation == "anchor":
        data.edge_features["oslots"][node] = {1, 2}
        expected = "orphan_reading_anchors"
    elif mutation == "delete_witness":
        data.edge_features["witness"].pop(node)
        expected = "orphan_readings"
    else:
        wrong_witness = _node(data, "manuscript", "ms_abbrev", "A")
        data.edge_features["witness"][node] = {wrong_witness}
        expected = "orphan_readings"

    report = build_conversion_report(tmp_path, books, data)
    assert report["status"] == "failed"
    assert report["semantic_checks"][expected] is False


def test_orphan_witness_audit_rejects_cross_version_target(tmp_path):
    books, data = _case(tmp_path, "orphan_reading.xml")
    node = _node(data, "orphan_reading")
    witness = next(iter(data.edge_features["witness"][node]))
    data.node_features["version_id"][witness] = "wrong-version"

    report = build_conversion_report(tmp_path, books, data)
    assert report["status"] == "failed"
    assert report["semantic_checks"]["orphan_witness_ownership"] is False


def test_legacy_chapter_verse_source_remains_supported():
    book = parse_file(FIXTURES / "legacy.xml")
    assert book.filename == "Legacy"
    assert book.versions[0].divs[0].children[0].number == "20"
