from pathlib import Path

from pseudepigrapha_tf.audit import build_conversion_report
from pseudepigrapha_tf.graph import build_tf_data
from pseudepigrapha_tf.source import load_source_directory

FIXTURES = Path(__file__).parent / "fixtures"


def _corpus(tmp_path):
    for name in ("sample.xml", "three_divisions.xml", "legacy.xml"):
        (tmp_path / name).write_text((FIXTURES / name).read_text(encoding="utf-8"), encoding="utf-8")
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    return books


def test_conversion_report_proves_semantic_parity_against_raw_xml(tmp_path):
    books = _corpus(tmp_path)
    data = build_tf_data(books, upstream_commit="abc123")
    report = build_conversion_report(tmp_path, books, data)

    assert report["status"] == "ok"
    assert report["semantic_checks"]
    assert all(report["semantic_checks"].values())
    assert report["graph"]["slots"] == data.max_slot
    assert report["graph"]["oslots_edges"] == data.oslots_edge_count
    assert report["source"]["readings"] == len([n for n, kind in data.node_features["otype"].items() if kind == "reading"])
    assert report["provenance"]["upstream_commit"] == "abc123"


def test_conversion_report_detects_silent_reading_corruption(tmp_path):
    books = _corpus(tmp_path)
    data = build_tf_data(books)
    reading = next(n for n, kind in data.node_features["otype"].items() if kind == "reading")
    data.node_features["reading_text"][reading] = "CORRUPTED"

    report = build_conversion_report(tmp_path, books, data)
    assert report["status"] == "failed"
    assert report["semantic_checks"]["reading_payloads"] is False
