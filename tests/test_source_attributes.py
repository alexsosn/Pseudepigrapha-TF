from pathlib import Path

import pytest

from pseudepigrapha_tf import audit
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory
from pseudepigrapha_tf.source_structure import LEGACY_ATTRIBUTES, MODERN_ATTRIBUTES


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


def _without_attribute(element_start: bytes, attribute: bytes) -> bytes:
    data = _modern_xml()
    replacement = element_start.replace(b" " + attribute, b"", 1)
    assert replacement != element_start
    return data.replace(element_start, replacement, 1)


def _missing_manuscript_language(*, book_filename: str = "Attrs") -> bytes:
    data = _without_attribute(
        b'<ms abbrev="A" language="Greek" show="yes">',
        b'language="Greek"',
    )
    if book_filename != "Attrs":
        data = data.replace(b'filename="Attrs"', f'filename="{book_filename}"'.encode(), 1)
    return data


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


@pytest.mark.parametrize(
    ("element", "element_start", "attribute", "name"),
    [
        ("book", b'<book filename="Attrs" title="Attribute fixture" textStructure="criticalApparatus">', b'filename="Attrs"', "filename"),
        ("book", b'<book filename="Attrs" title="Attribute fixture" textStructure="criticalApparatus">', b'title="Attribute fixture"', "title"),
        ("version", b'<version title="Greek" author="Anonymous" language="Greek" fragment="vfrag">', b'title="Greek"', "title"),
        ("version", b'<version title="Greek" author="Anonymous" language="Greek" fragment="vfrag">', b'author="Anonymous"', "author"),
        ("division", b'<division label="Chapter" delimiter=":"/>', b'label="Chapter"', "label"),
        ("resource", b'<resource name="Edition">', b'name="Edition"', "name"),
        ("ms", b'<ms abbrev="A" language="Greek" show="yes">', b'abbrev="A"', "abbrev"),
        ("ms", b'<ms abbrev="A" language="Greek" show="yes">', b'show="yes"', "show"),
        ("div", b'<div number="1" fragment="dfrag">', b'number="1"', "number"),
        ("unit", b'<unit id="1" group="2" parallel="p" linebreak="following">', b'id="1"', "id"),
        ("reading", b'<reading option="0" mss="A " linebreak="following" indent="1">', b'option="0"', "option"),
        ("reading", b'<reading option="0" mss="A " linebreak="following" indent="1">', b'mss="A "', "mss"),
    ],
)
def test_parser_rejects_missing_modern_dtd_required_attribute(element, element_start, attribute, name):
    with pytest.raises(
        InvalidSourceError,
        match=rf"missing required attribute {name} on <{element}>",
    ):
        parse_bytes(
            _without_attribute(element_start, attribute),
            source_path="attributes.xml",
        )


def test_non_exception_file_missing_manuscript_language_is_rejected():
    with pytest.raises(
        InvalidSourceError,
        match=r"Other.xml: missing required attribute language on <ms> at /book/version/manuscripts/ms",
    ):
        parse_bytes(_missing_manuscript_language(), source_path="Other.xml")


def test_exception_filename_does_not_exempt_wrong_book_identity():
    with pytest.raises(
        InvalidSourceError,
        match=r"ClMal.xml: missing required attribute language on <ms> at /book/version/manuscripts/ms",
    ):
        parse_bytes(_missing_manuscript_language(book_filename="Attrs"), source_path="ClMal.xml")


def test_raw_audit_rejects_same_unknown_attribute(tmp_path):
    path = tmp_path / "attributes.xml"
    path.write_bytes(_with_attribute(b'<unit id="1" group="2" parallel="p" linebreak="following">', b'future="metadata"'))

    with pytest.raises(InvalidSourceError, match=r"unsupported attribute future on <unit>"):
        audit._raw_inventory(tmp_path)


def test_raw_audit_rejects_missing_modern_dtd_required_attribute(tmp_path):
    path = tmp_path / "attributes.xml"
    path.write_bytes(
        _without_attribute(
            b'<unit id="1" group="2" parallel="p" linebreak="following">',
            b'id="1"',
        )
    )

    with pytest.raises(InvalidSourceError, match=r"missing required attribute id on <unit>"):
        audit._raw_inventory(tmp_path)


def test_only_fully_preserved_mixed_xml_elements_allow_arbitrary_attributes():
    expected = {"w", "sup", "booktitle"}
    assert {name for name, policy in MODERN_ATTRIBUTES.items() if policy is None} == expected
    assert {name for name, policy in LEGACY_ATTRIBUTES.items() if policy is None} == expected


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


def test_optional_modern_attributes_can_still_be_absent():
    data = _modern_xml()
    for element_start, attribute in (
        (b'<book filename="Attrs" title="Attribute fixture" textStructure="criticalApparatus">', b'textStructure="criticalApparatus"'),
        (b'<version title="Greek" author="Anonymous" language="Greek" fragment="vfrag">', b'fragment="vfrag"'),
        (b'<division label="Chapter" delimiter=":"/>', b'delimiter=":"'),
        (b'<unit id="1" group="2" parallel="p" linebreak="following">', b'parallel="p"'),
        (b'<reading option="0" mss="A " linebreak="following" indent="1">', b'indent="1"'),
    ):
        replacement = element_start.replace(b" " + attribute, b"", 1)
        data = data.replace(element_start, replacement, 1)
    assert parse_bytes(data, source_path="optional-attributes.xml").filename == "Attrs"


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


def test_duplicate_delimiter_spellings_fail_loudly_in_parser():
    data = _modern_xml().replace(
        b'<division label="Chapter" delimiter=":"/>',
        b'<division label="Chapter" delimiter=":" Delimiter="."/>',
        1,
    )

    with pytest.raises(InvalidSourceError, match=r"both delimiter and Delimiter on <division>"):
        parse_bytes(data, source_path="attributes.xml")


def test_duplicate_delimiter_spellings_fail_loudly_in_raw_audit(tmp_path):
    data = _modern_xml().replace(
        b'<division label="Chapter" delimiter=":"/>',
        b'<division label="Chapter" delimiter=":" Delimiter="."/>',
        1,
    )
    path = tmp_path / "attributes.xml"
    path.write_bytes(data)

    with pytest.raises(InvalidSourceError, match=r"both delimiter and Delimiter on <division>"):
        audit._raw_inventory(tmp_path)


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
