"""Fail-closed XML singleton-child regression tests (#182)."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from pseudepigrapha_tf import audit
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes, parse_file


FIXTURES = Path(__file__).parent / "fixtures"


def _duplicate(parent: ET.Element, tag: str) -> None:
    original = parent.find(tag)
    assert original is not None, tag
    copy = deepcopy(original)
    if tag == "divisions":
        division = copy.find("division")
        assert division is not None
        division.set("label", "Unmodeled editorial division")
    elif tag == "manuscripts":
        ms = copy.find("ms")
        assert ms is not None
        ms.set("abbrev", "UNMODELED")
    elif tag == "text":
        div = copy.find("div")
        if div is not None:
            div.set("number", "UNMODELED")
        chapter = copy.find("chapter")
        if chapter is not None:
            chapter.set("number", "UNMODELED")
    elif tag in ("name", "URL"):
        copy.text = "UNMODELED extra value"
    parent.append(copy)


@pytest.mark.parametrize(("parent_path", "tag"), (
    ("version", "divisions"),
    ("version", "manuscripts"),
    ("version", "text"),
    ("version/manuscripts/ms", "name"),
    ("version/resources/resource", "URL"),
))
def test_modern_duplicate_singleton_element_is_rejected(parent_path, tag):
    root = ET.fromstring((FIXTURES / "sample.xml").read_bytes())
    parent = root.find(parent_path)
    assert parent is not None
    _duplicate(parent, tag)
    with pytest.raises(
        InvalidSourceError,
        match=rf"duplicate-modern[.]xml.*duplicate <{tag}> child of <{parent.tag}>",
    ):
        parse_bytes(ET.tostring(root), source_path="duplicate-modern.xml")


@pytest.mark.parametrize("tag", ("manuscripts", "text"))
def test_legacy_root_duplicate_singleton_is_rejected(tag):
    root = ET.fromstring((FIXTURES / "legacy.xml").read_bytes())
    _duplicate(root, tag)
    with pytest.raises(
        InvalidSourceError,
        match=rf"duplicate-legacy[.]xml.*duplicate <{tag}> child of <book>",
    ):
        parse_bytes(ET.tostring(root), source_path="duplicate-legacy.xml")


def _wrapped_legacy_root() -> ET.Element:
    root = ET.fromstring((FIXTURES / "legacy.xml").read_bytes())
    version = ET.Element("version", {"title": "Latin", "author": "", "language": "Latin"})
    for child in list(root):
        root.remove(child)
        version.append(child)
    root.append(version)
    assert parse_bytes(ET.tostring(root), source_path="wrapped.xml").versions
    return root


@pytest.mark.parametrize("tag", ("manuscripts", "text"))
def test_wrapped_legacy_version_duplicate_singleton_is_rejected(tag):
    root = _wrapped_legacy_root()
    version = root.find("version")
    assert version is not None
    _duplicate(version, tag)
    with pytest.raises(
        InvalidSourceError,
        match=rf"duplicate-wrapped[.]xml.*duplicate <{tag}> child of <version>",
    ):
        parse_bytes(ET.tostring(root), source_path="duplicate-wrapped.xml")


def test_source_raw_inventory_refuses_unmodeled_second_text(tmp_path):
    root = ET.fromstring((FIXTURES / "sample.xml").read_bytes())
    version = root.find("version")
    assert version is not None
    _duplicate(version, "text")
    (tmp_path / "duplicate.xml").write_bytes(ET.tostring(root))
    with pytest.raises(InvalidSourceError, match="duplicate[.]xml.*duplicate <text>"):
        audit._raw_inventory(tmp_path)


def test_intentionally_repeatable_source_children_stay_lossless():
    root = ET.fromstring((FIXTURES / "sample.xml").read_bytes())
    version = root.find("version")
    assert version is not None

    # Version resources and resource <info> are iterated via findall(), not
    # singleton lookups. Manuscript bibliography is likewise repeatable.
    resource = version.find("resources/resource")
    assert resource is not None
    ET.SubElement(resource, "info").text = "Later source note"
    existing_resources = version.find("resources")
    assert existing_resources is not None
    extra_resources = deepcopy(existing_resources)
    resource_copy = extra_resources.find("resource")
    assert resource_copy is not None
    resource_copy.set("name", "Secondary edition")
    version.append(extra_resources)

    ms = version.find("manuscripts/ms")
    assert ms is not None
    ET.SubElement(ms, "bibliography").text = "Second manuscript bibliography"

    extra_version = deepcopy(version)
    extra_version.set("title", "Second source version")
    root.append(extra_version)

    book = parse_bytes(ET.tostring(root), source_path="repeatable.xml")
    assert len(book.versions) == 2
    first = book.versions[0]
    assert len(first.resources) == 2
    assert first.resources[0].info[-1] == "Later source note"
    assert first.resources[1].name == "Secondary edition"
    assert "Later source note" in first.resources[1].info
    assert "Second manuscript bibliography" in first.manuscripts[0].bibliography
    assert len(first.divs[0].items) == 2
    assert len(first.divs[0].items[0].items[0].readings) == 2


def test_unmodified_modern_and_legacy_examples_remain_parseable():
    assert parse_file(FIXTURES / "sample.xml").versions
    assert parse_file(FIXTURES / "legacy.xml").versions
