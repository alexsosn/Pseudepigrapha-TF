"""TDD for bounded, source-grounded OCP nested-div errors (issue #198)."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from pseudepigrapha_tf import audit
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes, parse_file
from pseudepigrapha_tf.source_structure import SourceStructureError, validate_source_structure


def _deep_source(depth: int) -> bytes:
    """Well-formed OCP XML built without recursive ElementTree serialization."""
    assert depth > 0
    header = (
        '<book filename="Deep" title="Deep div source">'
        '<version title="Greek" author="Test" language="Greek">'
        '<divisions><division label="Chapter" delimiter=":">Source chapter</division></divisions>'
        '<manuscripts><ms abbrev="A" language="Greek" show="yes">'
        '<name>Witness A</name></ms></manuscripts><text>'
    )
    inner = '<unit id="u1"><reading option="0" mss="A">unlost scholarly text</reading></unit>'
    return (
        header
        + ('<div number="1">' * depth)
        + inner
        + ('</div>' * depth)
        + '</text></version></book>'
    ).encode("utf-8")


@pytest.mark.parametrize("depth", [129, 1100])
def test_parser_rejects_excessive_div_depth_as_invalid_source(depth):
    with pytest.raises(
        InvalidSourceError,
        match=r"deep[.]xml.*<div>.*nesting depth 129.*128",
    ):
        parse_bytes(_deep_source(depth), source_path="deep.xml")


def test_iterative_structure_validator_rejects_before_recursive_consumers():
    root = ET.fromstring(_deep_source(1100))
    with pytest.raises(
        SourceStructureError,
        match=r"deep-structure[.]xml.*<div>.*nesting depth.*128",
    ):
        validate_source_structure(root, legacy=False, source_path="deep-structure.xml")


def test_independent_raw_inventory_rejects_deep_source_before_recursive_audit(tmp_path):
    (tmp_path / "deep.xml").write_bytes(_deep_source(1100))
    with pytest.raises(
        InvalidSourceError,
        match=r"deep[.]xml.*<div>.*nesting depth.*128",
    ):
        audit._raw_inventory(tmp_path)


def test_ordinary_multilevel_division_preserves_every_level_and_final_reading():
    book = parse_bytes(_deep_source(32), source_path="acceptable.xml")
    assert book.filename == "Deep"
    assert len(book.versions) == 1
    div = book.versions[0].divs[0]
    for _ in range(31):
        assert div.number == "1"
        assert len(div.items) == 1
        div = div.items[0]
    assert div.number == "1"
    assert len(div.items) == 1
    unit = div.items[0]
    assert unit.unit_id == "u1"
    assert [reading.text for reading in unit.readings] == ["unlost scholarly text"]


def test_existing_modern_and_legacy_fixtures_still_parse():
    source = Path(__file__).parent / "fixtures"
    assert parse_file(source / "sample.xml").versions
    assert parse_file(source / "legacy.xml").versions
