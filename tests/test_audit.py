from pathlib import Path

import pytest

from pseudepigrapha_tf import audit as compatibility_audit
from pseudepigrapha_tf import semantic_audit
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
VERSION_METADATA_CORRUPTIONS = (
    ("title", "CORRUPTED TITLE"),
    ("text_structure", "CORRUPTED STRUCTURE"),
    ("author", "CORRUPTED AUTHOR"),
    ("language", "CORRUPTED LANGUAGE"),
    ("version_fragment", "CORRUPTED FRAGMENT"),
    ("source_file", "wrong-source.xml"),
    ("source_sha256", "0" * 64),
)


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


def test_conversion_report_reuses_section_address_resolution(monkeypatch, tmp_path):
    source = FIXTURES / "three_divisions.xml"
    (tmp_path / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    data = build_tf_data(books)

    calls = 0
    original = semantic_audit._section_address_records

    def counted(records_data):
        nonlocal calls
        calls += 1
        return original(records_data)

    monkeypatch.setattr(semantic_audit, "_section_address_records", counted)
    report = semantic_audit.build_conversion_report(tmp_path, books, data)

    assert report["status"] == "ok", report["failed_checks"]
    assert calls == 1


def test_conversion_report_preserves_invalid_section_address_semantics(monkeypatch, tmp_path):
    source = FIXTURES / "three_divisions.xml"
    (tmp_path / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    data = build_tf_data(books)

    monkeypatch.setattr(semantic_audit, "_section_address_records", lambda _: None)
    report = semantic_audit.build_conversion_report(tmp_path, books, data)

    assert report["status"] == "failed"
    assert report["semantic_checks"]["section_addresses_unique"] is False
    assert report["diagnostics"]["duplicate_section_addresses"] == []


def test_conversion_report_preserves_empty_source_division_without_section_fabrication(tmp_path):
    source = FIXTURES / "empty_division.xml"
    (tmp_path / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []

    data = build_tf_data(books)
    report = build_conversion_report(tmp_path, books, data)

    assert report["status"] == "ok", report["failed_checks"]
    assert all(report["semantic_checks"].values())
    assert report["source"]["divisions"] == report["graph"]["divisions"] == 3
    assert report["source"]["units"] == report["graph"]["units"] == 1
    assert report["semantic_checks"]["section_coverage"] is True
    assert report["semantic_checks"]["section_addresses_unique"] is True


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
            "address": ["Frag", "9.4b", first_address],
            "nodes": [first, second],
            "source_refs": source_refs,
        }
    ]


def test_duplicate_upstream_sections_get_unique_tf_addresses_without_changing_source_refs():
    data = build_tf_data([parse_file(FIXTURES / "duplicate_sections.xml")])
    verses = [n for n, kind in data.node_features["otype"].items() if kind == "verse"]

    assert [data.node_features["source_ref"][n] for n in verses] == [
        "10:4",
        "10:43",
        "10:4",
        "10:45",
    ]
    assert [data.node_features["verse"][n] for n in verses] == ["4", "43", "4~2", "45"]
    assert data.node_features["section_occurrence"][verses[0]] == 1
    assert data.node_features["section_occurrence"][verses[2]] == 2
    assert _section_address_collisions(data) == []
    assert any("duplicate source section '10:4'" in warning for warning in data.warnings)


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


def test_compatibility_audit_entry_point_matches_canonical_semantic_report(tmp_path):
    source = FIXTURES / "metadata_only_version.xml"
    (tmp_path / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    data = build_tf_data(books)

    canonical = build_conversion_report(tmp_path, books, data)
    compatibility = compatibility_audit.build_conversion_report(tmp_path, books, data)

    assert compatibility == canonical


def test_conversion_report_detects_silent_reading_corruption(tmp_path):
    books = _corpus(tmp_path)
    data = build_tf_data(books)
    reading = next(n for n, kind in data.node_features["otype"].items() if kind == "reading")
    data.node_features["reading_text"][reading] = "CORRUPTED"

    report = build_conversion_report(tmp_path, books, data)
    assert report["status"] == "failed"
    assert report["semantic_checks"]["reading_payloads"] is False


@pytest.mark.parametrize(("feature", "corrupted"), VERSION_METADATA_CORRUPTIONS)
def test_conversion_report_detects_silent_version_metadata_corruption(tmp_path, feature, corrupted):
    books = _corpus(tmp_path)
    data = build_tf_data(books)
    book = next(n for n, kind in data.node_features["otype"].items() if kind == "book")
    data.node_features.setdefault(feature, {})[book] = corrupted

    report = build_conversion_report(tmp_path, books, data)

    assert report["status"] == "failed"
    assert report["semantic_checks"]["versions"] is False


@pytest.mark.parametrize(("feature", "corrupted"), VERSION_METADATA_CORRUPTIONS)
def test_conversion_report_detects_metadata_only_version_metadata_corruption(tmp_path, feature, corrupted):
    source = FIXTURES / "metadata_only_version.xml"
    (tmp_path / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []

    data = build_tf_data(books)
    metadata = next(n for n, kind in data.node_features["otype"].items() if kind == "version_metadata")
    data.node_features.setdefault(feature, {})[metadata] = corrupted

    report = build_conversion_report(tmp_path, books, data)

    assert report["status"] == "failed"
    assert report["semantic_checks"]["versions"] is False
