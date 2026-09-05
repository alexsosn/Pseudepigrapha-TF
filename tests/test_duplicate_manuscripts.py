from pathlib import Path

import pytest

from pseudepigrapha_tf import audit
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes


def _version(title: str, manuscript_xml: str) -> str:
    return f'''<version title="{title}" author="Anonymous" language="Greek">
  <divisions><division label="Chapter"/></divisions>
  <manuscripts>{manuscript_xml}</manuscripts>
  <text><div number="1"><unit id="1"><reading option="0" mss="A ">alpha</reading></unit></div></text>
</version>'''


def _ms(abbrev: str = "A", name: str = "Witness A") -> str:
    return f'<ms abbrev="{abbrev}" language="Greek" show="yes"><name>{name}</name></ms>'


def _modern(*versions: str) -> bytes:
    return (
        '<book filename="DupMs" title="Duplicate manuscript fixture">'
        + "".join(versions)
        + "</book>"
    ).encode()


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
