from __future__ import annotations

from pathlib import Path

import pytest

from pseudepigrapha_tf.audit import _raw_inventory
from pseudepigrapha_tf.parser import InvalidSourceError
from pseudepigrapha_tf.source import load_source_directory


def _modern_book(*versions: str) -> str:
    return f'''<?xml version="1.0"?>
<book filename="Demo" title="Demo">
{''.join(versions)}
</book>
'''


def _version(
    *,
    title: str,
    language: str,
    manuscript: str,
    reading_mss: str | None = None,
    extra_manuscript: str = "",
) -> str:
    witness = reading_mss if reading_mss is not None else manuscript
    return f'''
  <version title="{title}" author="Editor" language="{language}">
    <divisions>
      <division label="Chapter" delimiter=":"/>
      <division label="Verse"/>
    </divisions>
    <manuscripts>
      <ms abbrev="{manuscript}" language="{language}" show="yes"><name>{manuscript}</name></ms>
      {extra_manuscript}
    </manuscripts>
    <text>
      <div number="1"><div number="1">
        <unit id="1"><reading option="0" mss="{witness} ">{title} text</reading></unit>
      </div></div>
    </text>
  </version>
'''


def test_loader_excludes_explicit_ocp_generated_translation(tmp_path: Path) -> None:
    xml = _modern_book(
        _version(title="Greek", language="Greek", manuscript="A"),
        _version(title="English", language="English", manuscript="OCP-Trans"),
    )
    (tmp_path / "Demo.xml").write_text(xml, encoding="utf-8")

    books, warnings = load_source_directory(tmp_path)

    assert [version.title for version in books[0].versions] == ["Greek"]
    assert any("generated translation" in warning and "English" in warning for warning in warnings)

    raw = _raw_inventory(tmp_path)
    assert [record["version_title"] for record in raw["versions"]] == ["Greek"]
    assert raw["excluded_generated_translation_versions"] == [
        {
            "ocp_book": "Demo",
            "version_title": "English",
            "language": "English",
            "source_file": "Demo.xml",
            "marker": "OCP-Trans",
        }
    ]


def test_loader_rejects_ambiguous_ocp_translation_marker(tmp_path: Path) -> None:
    xml = _modern_book(
        _version(
            title="Mixed",
            language="English",
            manuscript="OCP-Trans",
            extra_manuscript='<ms abbrev="A" language="Greek" show="yes"><name>A</name></ms>',
        )
    )
    (tmp_path / "Demo.xml").write_text(xml, encoding="utf-8")

    with pytest.raises(InvalidSourceError, match="OCP-Trans.*mixed|mixed.*OCP-Trans"):
        load_source_directory(tmp_path)


def test_wrapped_legacy_version_keeps_chapter_verse_semantics(tmp_path: Path) -> None:
    xml = '''<?xml version="1.0"?>
<book filename="Esdr" title="4 Ezra" language="Latin">
  <version title="4 Ezra" language="Latin" author="Anonymous">
    <manuscripts>
      <ms abbrev="Weber" language="Latin" show="yes"><name>Weber</name></ms>
    </manuscripts>
    <text>
      <chapter number="3">
        <verse reference="1">
          <unit id="1"><reading option="0" mss="Weber ">Latin text</reading></unit>
        </verse>
      </chapter>
    </text>
  </version>
</book>
'''
    (tmp_path / "Esdr.xml").write_text(xml, encoding="utf-8")

    books, warnings = load_source_directory(tmp_path)

    assert warnings == []
    version = books[0].versions[0]
    assert [(spec.label, spec.delimiter) for spec in version.divisions] == [
        ("Chapter", ":"),
        ("Verse", ""),
    ]
    assert version.divs[0].number == "3"
    assert version.divs[0].children[0].number == "1"
    assert version.divs[0].children[0].units[0].unit_id == "1"
