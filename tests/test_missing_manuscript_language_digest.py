"""TDD regressions: borrowed missing-language exceptions must fail for changed XML.

Issue #202. This test-only commit intentionally fails until source digest
verification is implemented. It must run before the implementation commit.
"""

import pytest

from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes


KNOWN = (
    ("ClMal.xml", "ClMal", "Jewish Antiquities", "Niese"),
    ("ClMal.xml", "ClMal", "Praep. Evang.", "Mras"),
    ("Eup.xml", "Eup", "Praep. Evang. (Frag. 3)", "Mras"),
    ("Ps-Eup.xml", "Ps-Eup", "Praep. Evang. (Frag. 1)", "Mras"),
    ("Ps-Eup.xml", "Ps-Eup", "Praep. Evang. (Frag. 2)", "Mras"),
)


def _spoofed_source(book_name: str, version_title: str, abbreviation: str, *, extra: str = "") -> bytes:
    return f"""<book filename="{book_name}" title="Changed upstream">
  <version title="{version_title}" author="Different editor" language="Greek">
    <divisions><division label="Chapter"/></divisions>
    <manuscripts>
      <ms abbrev="{abbreviation}" show="yes"><name>Unknown language</name></ms>
    </manuscripts>
    <text><div number="1"><unit id="1">
      <reading option="0" mss="{abbreviation}">alpha{extra}</reading>
    </unit></div></text>
  </version>
</book>""".encode()


@pytest.mark.parametrize("name,book,version,abbreviation", KNOWN)
def test_borrowed_exemption_rejected_without_exact_source_digest(name, book, version, abbreviation):
    forged = _spoofed_source(book, version, abbreviation)
    with pytest.raises(InvalidSourceError, match=r"missing required attribute language on <ms>"):
        parse_bytes(forged, source_path=name)


def test_unreviewed_byte_change_cannot_borrow_known_record_identity():
    name, book, version, abbreviation = KNOWN[0]
    initial = _spoofed_source(book, version, abbreviation)
    changed = _spoofed_source(book, version, abbreviation, extra=" beta")
    assert initial != changed
    for payload in (initial, changed):
        with pytest.raises(InvalidSourceError, match=r"missing required attribute language on <ms>"):
            parse_bytes(payload, source_path=name)
