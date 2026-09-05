from pathlib import Path

import pytest

from pseudepigrapha_tf import audit
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes, parse_file

FIXTURES = Path(__file__).parent / "fixtures"


def _modern_xml(*, version_extra="", division_extra="", div_extra="", unit_extra="", reading_extra="") -> bytes:
    return f'''<book filename="Drift" title="Schema drift" textStructure="criticalApparatus">
  <version title="Greek" author="Anonymous" language="Greek">
    {version_extra}
    <divisions><division label="Chapter" delimiter=":" >{division_extra}</division></divisions>
    <manuscripts><ms abbrev="A" language="Greek" show="yes"><name>Witness A</name></ms></manuscripts>
    <text><div number="1">{div_extra}<unit id="1">{unit_extra}<reading option="0" mss="A ">alpha{reading_extra}</reading></unit></div></text>
  </version>
</book>'''.encode()


@pytest.mark.parametrize(
    ("parent", "kwargs"),
    [
        ("version", {"version_extra": "<future/>"}),
        ("division", {"division_extra": "<future>metadata</future>"}),
        ("div", {"div_extra": "<future><unit id='lost'/></future>"}),
        ("unit", {"unit_extra": "<future/>"}),
        ("reading", {"reading_extra": "<future>beta</future>"}),
    ],
)
def test_modern_parser_rejects_unsupported_direct_children(parent, kwargs):
    with pytest.raises(InvalidSourceError, match=rf"unsupported <future> child of <{parent}>"):
        parse_bytes(_modern_xml(**kwargs), source_path="drift.xml")


def test_raw_audit_rejects_same_schema_drift_instead_of_inventorying_it(tmp_path):
    (tmp_path / "drift.xml").write_bytes(_modern_xml(div_extra="<future/>"))

    with pytest.raises(InvalidSourceError, match=r"unsupported <future> child of <div>"):
        audit._raw_inventory(tmp_path)


def test_legacy_chapter_verse_source_remains_supported():
    book = parse_file(FIXTURES / "legacy.xml")
    assert book.filename == "Legacy"
    assert book.versions[0].divs[0].children[0].number == "20"
