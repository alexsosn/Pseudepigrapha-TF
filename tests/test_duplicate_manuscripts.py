from pathlib import Path

import pytest

from pseudepigrapha_tf import audit
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.model import Book, Div, DivisionSpec, Manuscript, Reading, Token, Unit, Version
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes


def _version(title: str, manuscript_xml: str) -> str:
    return f'''<version title="{title}" author="Anonymous" language="Greek">
  <divisions><division label="Chapter"/></divisions>
  <manuscripts>{manuscript_xml}</manuscripts>
  <text><div number="1"><unit id="1"><reading option="0" mss="A ">alpha</reading></unit></div></text>
</version>'''


def _ms(abbrev: str = "A", name: str = "Witness A") -> str:
    return f'<ms abbrev="{abbrev}" language="Greek" show="yes"><name>{name}</name></ms>'


def _ms_without_abbrev(name: str) -> str:
    return f'<ms language="Greek" show="yes"><name>{name}</name></ms>'


def _modern(*versions: str) -> bytes:
    return (
        '<book filename="DupMs" title="Duplicate manuscript fixture">'
        + "".join(versions)
        + "</book>"
    ).encode()


def _model_manuscript(name: str, abbrev: str = "A") -> Manuscript:
    return Manuscript(
        abbrev=abbrev,
        language="Greek",
        show="yes",
        name=name,
        name_xml=name,
        bibliography=(),
        bibliography_xml=(),
    )


def _model_book(*, manuscripts: tuple[Manuscript, ...], witnesses: tuple[str, ...]) -> Book:
    mss_raw = " ".join(witnesses) + (" " if witnesses else "")
    reading = Reading(
        option="0",
        witnesses=witnesses,
        mss_raw=mss_raw,
        linebreak="",
        indent="",
        text="alpha",
        content_xml="alpha",
        tokens=(Token("alpha"),),
    )
    version = Version(
        title="Greek",
        author="Anonymous",
        language="Greek",
        fragment="",
        divisions=(DivisionSpec("Chapter"),),
        resources=(),
        manuscripts=manuscripts,
        divs=(Div("1", "", (Unit("1", "0", "", "", (reading,)),)),),
    )
    return Book(
        filename="DupMs",
        title="Duplicate manuscript fixture",
        text_structure="",
        versions=(version,),
    )


def test_parser_rejects_duplicate_manuscript_abbreviation_within_version():
    data = _modern(_version("Greek", _ms(name="First") + _ms(name="Second")))

    with pytest.raises(
        InvalidSourceError,
        match=r"duplicates manuscript abbreviation 'A'.*version 'Greek'",
    ):
        parse_bytes(data, source_path="duplicate-ms.xml")


def test_raw_audit_rejects_duplicate_manuscript_abbreviation(tmp_path: Path):
    path = tmp_path / "duplicate-ms.xml"
    path.write_bytes(_modern(_version("Greek", _ms(name="First") + _ms(name="Second"))))

    with pytest.raises(
        InvalidSourceError,
        match=r"duplicates manuscript abbreviation 'A'.*version 'Greek'",
    ):
        audit._raw_inventory(tmp_path)


def test_same_manuscript_abbreviation_in_different_versions_is_allowed():
    book = parse_bytes(
        _modern(
            _version("Greek One", _ms(name="First")),
            _version("Greek Two", _ms(name="Second")),
        ),
        source_path="same-ms-different-versions.xml",
    )

    assert [version.manuscripts[0].abbrev for version in book.versions] == ["A", "A"]


def test_modern_missing_abbreviation_reports_required_attribute_not_duplicate():
    data = _modern(
        _version(
            "Greek",
            _ms_without_abbrev("First") + _ms_without_abbrev("Second"),
        )
    )

    with pytest.raises(
        InvalidSourceError,
        match=r"missing required attribute abbrev on <ms>",
    ):
        parse_bytes(data, source_path="missing-abbrev.xml")


def test_legacy_duplicate_manuscript_abbreviation_is_rejected():
    data = f'''<book filename="LegacyDup" title="Legacy duplicate" language="Greek">
  <manuscripts>{_ms(name="First")}{_ms(name="Second")}</manuscripts>
  <text><chapter number="1"><verse reference="1"><unit id="1"><reading option="0" mss="A ">alpha</reading></unit></verse></chapter></text>
</book>'''.encode()

    with pytest.raises(
        InvalidSourceError,
        match=r"duplicates manuscript abbreviation 'A'.*legacy version",
    ):
        parse_bytes(data, source_path="legacy-duplicate-ms.xml")


def test_legacy_multiple_manuscripts_without_abbreviation_are_not_ambiguous():
    data = f'''<book filename="LegacyNoAbbrev" title="Legacy metadata" language="Greek">
  <manuscripts>{_ms_without_abbrev("First")}{_ms_without_abbrev("Second")}</manuscripts>
  <text><chapter number="1"><verse reference="1"><unit id="1"><reading option="0" mss="">alpha</reading></unit></verse></chapter></text>
</book>'''.encode()

    book = parse_bytes(data, source_path="legacy-no-abbrev.xml")
    assert [ms.abbrev for ms in book.versions[0].manuscripts] == ["", ""]


def test_graph_builder_rejects_duplicate_manuscript_abbreviation_in_direct_model():
    book = _model_book(
        manuscripts=(_model_manuscript("First"), _model_manuscript("Second")),
        witnesses=("A",),
    )

    with pytest.raises(
        ValueError,
        match=r"DupMs/Greek: duplicate manuscript abbreviation 'A'",
    ):
        build_tf_data([book])


def test_graph_builder_allows_multiple_unaddressable_manuscripts_without_abbreviation():
    book = _model_book(
        manuscripts=(
            _model_manuscript("First", abbrev=""),
            _model_manuscript("Second", abbrev=""),
        ),
        witnesses=(),
    )

    data = build_tf_data([book])
    manuscript_nodes = [
        node
        for node, kind in data.node_features["otype"].items()
        if kind == "manuscript"
    ]
    assert len(manuscript_nodes) == 2
    assert all(data.node_features.get("ms_abbrev", {}).get(node, "") == "" for node in manuscript_nodes)
