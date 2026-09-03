from pathlib import Path

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.graph import TFData
from pseudepigrapha_tf.parser import parse_file
from pseudepigrapha_tf.semantic_audit import (
    _section_address_collisions,
    _section_coverage_ok,
    build_conversion_report,
)
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


def test_section_coverage_computes_slot_bound_once():
    data = build_tf_data([parse_file(FIXTURES / "sample.xml")])

    class CountingTFData(TFData):
        max_slot_calls = 0

        @property
        def max_slot(self):
            self.max_slot_calls += 1
            return super().max_slot

    counted = CountingTFData(
        data.node_features,
        data.edge_features,
        data.metadata,
        data.warnings,
    )
    assert _section_coverage_ok(counted) is True
    assert counted.max_slot_calls == 1


def test_section_address_collisions_report_nodes_and_source_refs():
    data = build_tf_data([parse_file(FIXTURES / "three_divisions.xml")])
    verses = [n for n, kind in data.node_features["otype"].items() if kind == "verse"]
    assert len(verses) == 2
    first, second = verses
    first_address = data.node_features["verse"][first]
    source_refs = [data.node_features["source_ref"][node] for node in verses]

    data.node_features["verse"][second] = first_address
    collisions = _section_address_collisions(data)

    assert collisions == [
        {
            "address": ["Deep", "9.4b", first_address],
            "nodes": [first, second],
            "source_refs": source_refs,
        }
    ]


def test_conversion_report_includes_metadata_only_versions(tmp_path):
    source = FIXTURES / "metadata_only_version.xml"
    (tmp_path / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []

    data = build_tf_data(books)
    report = build_conversion_report(tmp_path, books, data)
    assert report["status"] == "ok", report["failed_checks"]
    assert report["source"]["versions"] == 2
    assert report["graph"]["versions"] == 2
    assert report["graph"]["metadata_only_versions"] == 1
    assert report["source"]["manuscripts"] == report["graph"]["manuscripts"] == 2


def test_conversion_report_detects_silent_reading_corruption(tmp_path):
    books = _corpus(tmp_path)
    data = build_tf_data(books)
    reading = next(n for n, kind in data.node_features["otype"].items() if kind == "reading")
    data.node_features["reading_text"][reading] = "CORRUPTED"

    report = build_conversion_report(tmp_path, books, data)
    assert report["status"] == "failed"
    assert report["semantic_checks"]["reading_payloads"] is False
