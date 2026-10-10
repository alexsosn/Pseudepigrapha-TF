"""Lossless source-boundary regression for structural XML mixed content (#180)."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from pseudepigrapha_tf import audit
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes, parse_file
from pseudepigrapha_tf.source_structure import validate_source_structure


FIXTURES = Path(__file__).parent / "fixtures"
MODERN_XML = b"""<book filename="Drift" title="Mixed source" textStructure="criticalApparatus">
<version title="Greek" author="Editor" language="Greek">
<divisions><division label="Chapter" delimiter=":">Chapter description</division></divisions>
<resources><resource name="Edition"><info>Source info</info><URL>https://example.test</URL></resource></resources>
<manuscripts><ms abbrev="A" language="Greek" show="yes"><name>Codex <sup>A</sup> shelf</name><bibliography>Bibliography <booktitle>Book</booktitle> tail</bibliography></ms></manuscripts>
<text><div number="1"><unit id="1"><reading option="0" mss="A">alpha <w lex="lemma" morph="N">beta</w> gamma</reading></unit></div></text>
</version>
</book>"""


MODERN_STRUCTURAL_PATHS = (
    (".", "book"),
    ("version", "version"),
    ("version/divisions", "divisions"),
    ("version/resources", "resources"),
    ("version/resources/resource", "resource"),
    ("version/manuscripts", "manuscripts"),
    ("version/manuscripts/ms", "ms"),
    ("version/text", "text"),
    ("version/text/div", "div"),
    ("version/text/div/unit", "unit"),
)


def _inject(source: bytes, parent_path: str, location: str) -> bytes:
    root = ET.fromstring(source)
    parent = root if parent_path == "." else root.find(parent_path)
    assert parent is not None, parent_path
    if location == "direct text":
        parent.text = (parent.text or "") + " UNMODELED_SOURCE_WORD "
    else:
        assert location == "child tail"
        first = list(parent)[0]
        first.tail = (first.tail or "") + "\r\n UNMODELED_SOURCE_WORD\t"
    return ET.tostring(root, encoding="utf-8")


@pytest.mark.parametrize(("path", "tag"), MODERN_STRUCTURAL_PATHS)
@pytest.mark.parametrize("location", ("direct text", "child tail"))
def test_modern_structural_mixed_text_is_rejected_before_conversion(path, tag, location):
    data = _inject(MODERN_XML, path, location)
    with pytest.raises(InvalidSourceError, match=rf"drift\.xml.*<{tag}>.*(text|tail)"):
        parse_bytes(data, source_path="drift.xml")


@pytest.mark.parametrize(("path", "tag"), (
    ("resources", "resources"),
    ("resources/resource", "resource"),
    ("manuscripts", "manuscripts"),
    ("manuscripts/ms", "ms"),
    ("text", "text"),
    ("text/chapter", "chapter"),
    ("text/chapter/verse", "verse"),
    ("text/chapter/verse/unit", "unit"),
))
@pytest.mark.parametrize("location", ("direct text", "child tail"))
def test_legacy_structural_mixed_text_is_rejected(path, tag, location):
    source = (FIXTURES / "legacy.xml").read_bytes()
    with pytest.raises(InvalidSourceError, match=rf"legacy\.xml.*<{tag}>.*(text|tail)"):
        parse_bytes(_inject(source, path, location), source_path="legacy.xml")


def test_wrapped_legacy_source_does_not_lose_direct_chapter_text():
    root = ET.fromstring((FIXTURES / "legacy.xml").read_bytes())
    version = ET.Element("version", {"title": "Latin", "author": "", "language": "Latin"})
    for child in list(root):
        root.remove(child)
        version.append(child)
    root.append(version)
    # First verify that this is the supported wrapped-legacy dialect.
    assert parse_bytes(ET.tostring(root), source_path="wrapped.xml").versions[0].divs
    chapter = root.find("version/text/chapter")
    assert chapter is not None
    chapter.text = "LOST LEGACY CHAPTER"
    with pytest.raises(InvalidSourceError, match=r"wrapped\.xml.*<chapter>.*text"):
        parse_bytes(ET.tostring(root), source_path="wrapped.xml")


def test_independent_raw_audit_rejects_unmodeled_interstitial_text(tmp_path):
    (tmp_path / "drift.xml").write_bytes(
        _inject(MODERN_XML, "version/text/div/unit", "child tail")
    )
    with pytest.raises(InvalidSourceError, match=r"drift\.xml.*<unit>.*tail"):
        audit._raw_inventory(tmp_path)


def test_legitimate_mixed_content_and_crlf_indentation_are_preserved():
    source = MODERN_XML.replace(b"\n", b"\r\n")
    root = ET.fromstring(source)
    valid_text = root.find("version/text/div/unit/reading")
    assert valid_text is not None
    before = (valid_text.text, valid_text[0].tail)
    validate_source_structure(root, legacy=False, source_path="accepted.xml")
    assert (valid_text.text, valid_text[0].tail) == before

    book = parse_bytes(source, source_path="accepted.xml")
    version = book.versions[0]
    assert version.divisions[0].text == "Chapter description"
    assert version.resources[0].info == ("Source info",)
    assert version.resources[0].url == "https://example.test"
    assert version.manuscripts[0].name == "Codex A shelf"
    assert version.manuscripts[0].bibliography == ("Bibliography Book tail",)
    reading = version.divs[0].items[0].readings[0]
    assert reading.text == "alpha beta gamma"
    assert reading.tokens[1].text == "beta"
    assert reading.tokens[2].text == "gamma"
    assert "<w lex=" in reading.content_xml


def test_existing_upstream_mixed_content_fixtures_still_parse():
    modern = parse_file(FIXTURES / "sample.xml")
    assert modern.versions[0].manuscripts[0].name == "Codex A"
    assert any(token.annotated for token in modern.versions[0].divs[0].items[0].items[0].readings[0].tokens)
    legacy = parse_file(FIXTURES / "legacy.xml")
    assert legacy.versions[0].divs[0].items[0].items[0].readings[0].text == "Initium verbi"


@pytest.mark.parametrize("codepoint", (0x00A0, 0x2007, 0x2028))
@pytest.mark.parametrize("location", ("direct text", "child tail"))
def test_non_xml_unicode_whitespace_is_not_discarded(codepoint, location):
    # Python str.isspace() includes NBSP, figure space and line separator.
    # Those are not XML indentation (XML S = #x20 | #x9 | #xD | #xA):
    # losing them from an otherwise structural div is still source loss.
    symbol = chr(codepoint)
    root = ET.fromstring(MODERN_XML)
    parent = root.find("version/text/div")
    assert parent is not None
    if location == "direct text":
        parent.text = symbol
    else:
        parent[0].tail = symbol
    with pytest.raises(InvalidSourceError, match=r"unicode-space[.]xml.*<div>.*(text|tail)"):
        parse_bytes(ET.tostring(root), source_path="unicode-space.xml")
