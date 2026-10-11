"""Reject distinct XML files declaring one indistinguishable OCP work identity."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from pseudepigrapha_tf import audit
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import InvalidSourceError, parse_file
from pseudepigrapha_tf.source import load_source_directory


SOURCE = Path(__file__).parent / "fixtures" / "sample.xml"


def _two_files(directory: Path, *, identical_id: bool = True) -> tuple[Path, Path]:
    first = directory / "first.xml"
    second = directory / "second.xml"
    first.write_bytes(SOURCE.read_bytes())
    second_data = SOURCE.read_bytes().replace("λόγος".encode(), "λόγος".encode(), 1)
    assert second_data != first.read_bytes()
    if not identical_id:
        second_data = second_data.replace(b'filename="Sample"', b'filename="Other"')
    second.write_bytes(second_data)
    return first, second


def test_source_directory_rejects_two_distinct_documents_with_same_book_filename(tmp_path):
    _two_files(tmp_path)
    with pytest.raises(
        InvalidSourceError, match=r"duplicate.*Sample.*first[.]xml.*second[.]xml"
    ):
        load_source_directory(tmp_path)


def test_graph_builder_rejects_colliding_work_identifiers_even_without_directory_loader(tmp_path):
    first, second = _two_files(tmp_path)
    books = [parse_file(first), parse_file(second)]
    assert books[0].filename == books[1].filename == "Sample"
    with pytest.raises(ValueError, match=r"duplicate.*(?:book|work).*Sample"):
        build_tf_data(books)


def test_independent_raw_audit_detects_same_work_id_across_source_files(tmp_path):
    _two_files(tmp_path)
    with pytest.raises(
        InvalidSourceError, match=r"duplicate.*Sample.*first[.]xml.*second[.]xml"
    ):
        audit._raw_inventory(tmp_path)


def test_distinct_work_ids_with_identical_version_titles_remain_supported(tmp_path):
    _two_files(tmp_path, identical_id=False)
    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    assert [book.filename for book in books] == ["Sample", "Other"]
    assert [book.versions[0].title for book in books] == ["Greek", "Greek"]

    graph = build_tf_data(books)
    assert {"Sample", "Other"}.issubset(set(graph.node_features["ocp_book"].values()))
    raw = audit._raw_inventory(tmp_path)
    assert {version["ocp_book"] for version in raw["versions"]} == {"Sample", "Other"}


def test_multiple_versions_inside_one_document_are_not_cross_file_duplicates(tmp_path):
    root = ET.fromstring(SOURCE.read_bytes())
    first_version = root.find("version")
    assert first_version is not None
    second_version = deepcopy(first_version)
    second_version.set("title", "Second legitimate version")
    root.append(second_version)
    (tmp_path / "one-work.xml").write_bytes(ET.tostring(root, encoding="utf-8"))

    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    assert len(books) == 1
    assert [version.title for version in books[0].versions] == [
        "Greek", "Second legitimate version",
    ]
    graph = build_tf_data(books)
    assert graph is not None
    assert len(audit._raw_inventory(tmp_path)["versions"]) == 2
