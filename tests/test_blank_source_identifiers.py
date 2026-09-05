from pathlib import Path

import pytest

from pseudepigrapha_tf import audit
from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.model import Book, Div, DivisionSpec, Manuscript, Reading, Token, Unit, Version
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes


def _modern_xml(
    *,
    filename: str = "Identity",
    version_title: str = "Greek",
    author: str = "Anonymous",
    ms_abbrev: str = "A",
    ms_language: str = "Greek",
    ms_show: str = "yes",
    div_number: str = "1",
    unit_id: str = "1",
    option: str = "0",
    mss: str = "A ",
) -> bytes:
    return f'''<book filename="{filename}" title="Identity fixture">
  <version title="{version_title}" author="{author}" language="Greek">
    <divisions><division label="Chapter"/></divisions>
    <manuscripts>
      <ms abbrev="{ms_abbrev}" language="{ms_language}" show="{ms_show}"><name>Witness A</name></ms>
    </manuscripts>
    <text>
      <div number="{div_number}">
        <unit id="{unit_id}">
          <reading option="{option}" mss="{mss}">alpha</reading>
        </unit>
      </div>
    </text>
  </version>
</book>'''.encode()


@pytest.mark.parametrize(
    ("attribute", "kwargs"),
    [
        ("filename", {"filename": ""}),
        ("abbrev", {"ms_abbrev": ""}),
        ("number", {"div_number": ""}),
        ("id", {"unit_id": ""}),
        ("option", {"option": ""}),
        ("filename", {"filename": "   "}),
        ("abbrev", {"ms_abbrev": "   "}),
        ("number", {"div_number": "   "}),
        ("id", {"unit_id": "   "}),
        ("option", {"option": "   "}),
    ],
)
def test_modern_parser_rejects_blank_identity_attributes(attribute, kwargs):
    with pytest.raises(
        InvalidSourceError,
        match=rf"blank required identity attribute {attribute}",
    ):
        parse_bytes(_modern_xml(**kwargs), source_path="blank-identity.xml")


def test_intentional_empty_metadata_and_witness_list_remain_supported():
    book = parse_bytes(
        _modern_xml(
            version_title="",
            author="",
            ms_language="",
            ms_show="",
            mss="",
        ),
        source_path="intentional-empty-metadata.xml",
    )

    version = book.versions[0]
    assert version.title == ""
    assert version.author == ""
    assert version.manuscripts[0].language == ""
    assert version.manuscripts[0].show == ""
    assert version.divs[0].units[0].readings[0].witnesses == ()


def test_raw_audit_rejects_blank_unit_identity(tmp_path: Path):
    path = tmp_path / "blank-unit.xml"
    path.write_bytes(_modern_xml(unit_id="   "))

    with pytest.raises(
        InvalidSourceError,
        match=r"blank required identity attribute id",
    ):
        audit._raw_inventory(tmp_path)


def _manuscript(abbrev: str = "A") -> Manuscript:
    return Manuscript(
        abbrev=abbrev,
        language="Greek",
        show="yes",
        name="Witness A",
        name_xml="Witness A",
        bibliography=(),
        bibliography_xml=(),
    )


def _model_book(
    *,
    filename: str = "Identity",
    ms_abbrev: str = "A",
    div_number: str = "1",
    unit_id: str = "1",
    option: str = "0",
) -> Book:
    witnesses = (ms_abbrev,) if ms_abbrev.strip() else ()
    reading = Reading(
        option=option,
        witnesses=witnesses,
        mss_raw=(f"{ms_abbrev} " if witnesses else ""),
        linebreak="",
        indent="",
        text="alpha",
        content_xml="alpha",
        tokens=(Token("alpha"),),
    )
    unit = Unit(
        unit_id=unit_id,
        group="0",
        parallel="",
        linebreak="",
        readings=(reading,),
    )
    version = Version(
        title="Greek",
        author="Anonymous",
        language="Greek",
        fragment="",
        divisions=(DivisionSpec("Chapter"),),
        resources=(),
        manuscripts=(_manuscript(ms_abbrev),),
        divs=(Div(div_number, "", (unit,)),),
    )
    return Book(
        filename=filename,
        title="Identity fixture",
        text_structure="",
        versions=(version,),
    )


@pytest.mark.parametrize(
    ("label", "kwargs"),
    [
        ("book filename", {"filename": "   "}),
        ("manuscript abbreviation", {"ms_abbrev": "   "}),
        ("div number", {"div_number": "   "}),
        ("unit id", {"unit_id": "   "}),
        ("reading option", {"option": "   "}),
    ],
)
def test_graph_builder_rejects_blank_direct_model_identities(label, kwargs):
    with pytest.raises(ValueError, match=rf"blank {label}"):
        build_tf_data([_model_book(**kwargs)])
