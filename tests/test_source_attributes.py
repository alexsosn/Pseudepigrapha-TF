from pathlib import Path

import pytest

from pseudepigrapha_tf import audit
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory


def _modern_xml() -> bytes:
    return b'''<book filename="Attrs" title="Attribute fixture" textStructure="criticalApparatus">
  <version title="Greek" author="Anonymous" language="Greek" fragment="vfrag">
    <divisions><division label="Chapter" delimiter=":"/></divisions>
    <resources><resource name="Edition"><info>edition</info><URL>https://example.test</URL></resource></resources>
    <manuscripts><ms abbrev="A" language="Greek" show="yes"><name>Witness A</name></ms></manuscripts>
    <text><div number="1" fragment="dfrag"><unit id="1" group="2" parallel="p" linebreak="following"><reading option="0" mss="A " linebreak="following" indent="1">alpha</reading></unit></div></text>
  </version>
</book>'''


def _with_attribute(element_start: bytes, attribute: bytes) -> bytes:
    data = _modern_xml()
    if element_start.endswith(b"/>"):
        replacement = element_start[:-2] + b" " + attribute + b"/>"
    else:
        replacement = element_start[:-1] + b" " + attribute + b">"
    return data.replace(element_start, replacement, 1)


@pytest.mark.parametrize(
    ("element", "element_start"),
    [
        ("book", b'<book filename="Attrs" title="Attribute fixture" textStructure="criticalApparatus">'),
        ("version", b'<version title="Greek" author="Anonymous" language="Greek" fragment="vfrag">'),
        ("division", b'<division label="Chapter" delimiter=":"/>'),
        ("resource", b'<resource name="Edition">'),
        ("ms", b'<ms abbrev="A" language="Greek" show="yes">'),
        ("div", b'<div number="1" fragment="dfrag">'),
        ("unit", b'<unit id="1" group="2" parallel="p" linebreak="following">'),
        ("reading", b'<reading option="0" mss="A " linebreak="following" indent="1">'),
        ("info", b'<info>'),
    ],
)
def test_parser_rejects_unknown_attribute_that_would_be_dropped(element, element_start):
    with pytest.raises(
        InvalidSourceError,
        match=rf"unsupported attribute future on <{element}>",
    ):
        parse_bytes(
            _with_attribute(element_start, b'future="metadata"'),
            source_path="attributes.xml",
        )


def test_raw_audit_rejects_same_unknown_attribute(tmp_path):
    path = tmp_path / "attributes.xml"
    path.write_bytes(_with_attribute(b'<unit id="1" group="2" parallel="p" linebreak="following">', b'future="metadata"'))

    with pytest.raises(InvalidSourceError, match=r"unsupported attribute future on <unit>"):
        audit._raw_inventory(tmp_path)


def test_all_modeled_modern_attributes_and_unit_linebreak_remain_supported():
    book = parse_bytes(_modern_xml(), source_path="attributes.xml")
    version = book.versions[0]
    div = version.divs[0]
    unit = div.units[0]
    reading = unit.readings[0]

    assert book.filename == "Attrs"
    assert book.text_structure == "criticalApparatus"
    assert version.fragment == "vfrag"
    assert version.divisions[0].delimiter == ":"
    assert version.resources[0].name == "Edition"
    assert version.manuscripts[0].show == "yes"
    assert div.fragment == "dfrag"
    assert (unit.group, unit.parallel, unit.linebreak) == ("2", "p", "following")
    assert (reading.linebreak, reading.indent) == ("following", "1")


def test_pinned_capitalized_delimiter_alias_is_preserved_and_audited(tmp_path):
    data = _modern_xml().replace(b'delimiter=":"', b'Delimiter=":"', 1)
    path = tmp_path / "attributes.xml"
    path.write_bytes(data)

    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    assert books[0].versions[0].divisions[0].delimiter == ":"

    graph = build_tf_data(books)
    report = build_conversion_report(tmp_path, books, graph)
    assert report["status"] == "ok", report["failed_checks"]
    assert report["semantic_checks"]["division_specs"] is True


def test_unknown_w_attribute_is_preserved_inside_audited_mixed_xml(tmp_path):
    data = _modern_xml().replace(
        b">alpha</reading>",
        b'>alpha <w morph="N" future="retained">beta</w></reading>',
        1,
    )
    path = tmp_path / "attributes.xml"
    path.write_bytes(data)

    books, warnings = load_source_directory(tmp_path)
    assert warnings == []
    reading = books[0].versions[0].divs[0].units[0].readings[0]
    assert 'future="retained"' in reading.content_xml

    graph = build_tf_data(books)
    report = build_conversion_report(tmp_path, books, graph)
    assert report["status"] == "ok", report["failed_checks"]


def test_legacy_modeled_attributes_remain_supported():
    legacy = b'''<book filename="LegacyAttrs" title="Legacy attributes" language="Latin">
  <manuscripts><ms abbrev="A" language="Latin" show="yes"><name>A</name></ms></manuscripts>
  <text><chapter number="8b" fragment="chapter-frag"><verse reference="20" fragment="verse-frag"><unit id="405" linebreak="following"><reading option="0" mss="A ">Initium</reading></unit></verse></chapter></text>
</book>'''
    book = parse_bytes(legacy, source_path="legacy-attributes.xml")
    chapter = book.versions[0].divs[0]
    verse = chapter.children[0]
    unit = verse.units[0]

    assert book.versions[0].language == "Latin"
    assert chapter.fragment == "chapter-frag"
    assert verse.fragment == "verse-frag"
    assert unit.linebreak == "following"
