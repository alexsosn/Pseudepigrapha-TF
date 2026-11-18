"""Compatibility regressions for OCP's new 5Ezra/6Ezra root language.

The fixture shape is taken from upstream OCP commit
853a64b623de296d2b8532a43593607772e7c45a, not a claim to
include the full upstream editions or their distinct apparatus evidence.
"""
from __future__ import annotations

import pytest

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes
from pseudepigrapha_tf.semantic_audit import build_conversion_report
from pseudepigrapha_tf.source import load_source_directory


def _modern_edition(*, work: str = "5Ezra", root_language: str = "Latin",
                    version_languages: tuple[str, ...] = ("Latin",)) -> bytes:
    # Keep the same Grammateus vocabulary and manuscript/reading arrangement
    # as the upstream 5Ezra and 6Ezra files.
    versions = []
    for index, language in enumerate(version_languages):
        versions.append(f"""
  <version title="Latin {index}" author="Anonymous" language="{language}">
    <divisions>
      <division label="Chapter" delimiter=":"/>
      <division label="Verse"/>
    </divisions>
    <manuscripts>
      <ms abbrev="Bensly" language="Latin" show="yes"><name>Bensly</name></ms>
      <ms abbrev="C" language="Latin" show="yes"><name>Codex C</name></ms>
    </manuscripts>
    <text><div number="1">
      <div number="1"><unit id="1">
        <reading option="0" mss="Bensly ">et venit</reading>
        <reading option="1" mss="C ">venit</reading>
      </unit></div>
      <div number="2"><unit id="1">
        <reading option="0" mss="Bensly ">et vidit</reading>
        <reading option="1" mss="C ">vidit</reading>
      </unit></div>
    </div></text>
  </version>""")
    return (f'<book filename="{work}" title="{work}" language="{root_language}">'
            + "".join(versions) + "</book>").encode("utf-8")


@pytest.mark.parametrize("work", ["5Ezra", "6Ezra"])
def test_redundant_modern_root_language_produces_audited_tf(work, tmp_path):
    raw = _modern_edition(work=work)
    book = parse_bytes(raw, source_path=f"{work}.xml")
    assert book.filename == work
    assert len(book.versions) == 1
    assert book.versions[0].language == "Latin"
    assert book.versions[0].divs[0].children[0].units[0].readings[0].text == "et venit"

    (tmp_path / f"{work}.xml").write_bytes(raw)
    books, warnings = load_source_directory(tmp_path)
    assert not warnings
    tf = build_tf_data(books)
    assert sum(t == "unit" for t in tf.node_features["otype"].values()) == 2
    assert sum(t == "reading" for t in tf.node_features["otype"].values()) == 4
    report = build_conversion_report(tmp_path, books, tf)
    assert report["status"] == "ok", report["failed_checks"]


def test_redundant_root_language_is_allowed_across_identical_versions():
    book = parse_bytes(_modern_edition(version_languages=("Latin", "Latin")))
    assert len(book.versions) == 2
    assert all(version.language == "Latin" for version in book.versions)


@pytest.mark.parametrize(
    ("root_language", "version_languages"),
    [
        ("Greek", ("Latin",)),
        ("", ("Latin",)),
        ("Latin", ("",)),
        ("Latin", ("Latin", "Greek")),
        ("Latin", ()),
    ],
)
def test_inconsistent_modern_root_language_fails_closed(root_language, version_languages):
    with pytest.raises(InvalidSourceError, match="root book language"):
        parse_bytes(_modern_edition(root_language=root_language, version_languages=version_languages))


def test_wrapped_legacy_root_language_remains_supported():
    wrapped = b"""<book filename="Legacy" title="Legacy" language="Latin">
      <version title="Latin" author="Anonymous" language="Latin">
        <manuscripts>
          <ms abbrev="A" language="Latin" show="yes"><name>A</name></ms>
        </manuscripts>
        <text><chapter number="1"><verse reference="1"><unit id="1">
          <reading option="0" mss="A ">text</reading>
        </unit></verse></chapter></text>
      </version>
    </book>"""
    book = parse_bytes(wrapped)
    assert book.versions[0].language == "Latin"


def test_namespaced_tei_is_not_misparsed_as_grammateus():
    raw = b'<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="ApDan"><text/></TEI>'
    with pytest.raises(InvalidSourceError, match="expected <book> root"):
        parse_bytes(raw, source_path="ApDan_TEI.xml")
