from pathlib import Path

import pytest

from pseudepigrapha_tf.parser import EmptySourceError, parse_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_parser_preserves_ocp_metadata_and_mixed_content():
    book = parse_file(FIXTURES / "sample.xml")

    assert book.filename == "Sample"
    assert book.title == "Sample Work"
    assert book.text_structure == "criticalApparatus"
    version = book.versions[0]
    assert [d.label for d in version.divisions] == ["Chapter", "Verse"]
    assert version.resources[0].info == ("Example edition", "Second note")
    assert version.manuscripts[0].name == "Codex A"
    assert "<sup>A</sup>" in version.manuscripts[0].name_xml

    unit = version.divs[0].children[0].units[0]
    assert unit.unit_id == "0"
    assert unit.group == "7"
    assert unit.parallel == "P1"
    primary = unit.readings[0]
    assert primary.witnesses == ("A", "B")
    assert primary.text == "λόγος θεοῦ"
    assert "<w" in primary.content_xml
    assert [t.text for t in primary.tokens] == ["λόγος", "θεοῦ"]
    assert primary.tokens[1].morph == "N"
    assert primary.tokens[1].lex == "θεός"


def test_empty_source_is_explicit():
    with pytest.raises(EmptySourceError):
        parse_file(FIXTURES / "empty.xml")


def test_legacy_book_chapter_verse_dialect_is_normalized_without_loss():
    book = parse_file(FIXTURES / "legacy.xml")
    version = book.versions[0]
    assert version.title == "Latin"
    assert version.language == "Latin"
    assert [d.label for d in version.divisions] == ["Chapter", "Verse"]
    assert version.resources[0].name == "Edition"
    assert version.divs[0].number == "8b"
    verse = version.divs[0].children[0]
    assert verse.number == "20"
    assert verse.units[0].unit_id == "405"
    assert verse.units[0].linebreak == "following"
