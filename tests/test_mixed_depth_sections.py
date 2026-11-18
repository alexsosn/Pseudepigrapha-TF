"""Mixed-depth Grammateus chapter/verse projection: OCP T12P source shape."""
from pathlib import Path

import pytest
from tf.fabric import Fabric

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import parse_bytes
from pseudepigrapha_tf.semantic_audit import _section_coverage_ok, build_conversion_report
from pseudepigrapha_tf.source import load_source_directory
from pseudepigrapha_tf.writer import write_tf


def _unit(unit_id: str, text: str) -> str:
    return (
        f'<unit id="{unit_id}"><reading option="0" mss="A ">'
        f'{text}</reading></unit>'
    )


def _source(inside_testament: str) -> bytes:
    return f'''<book filename="Depth" title="Depth">
      <version title="Greek" author="Anonymous" language="Greek">
        <divisions>
          <division label="Testament" delimiter=" "/>
          <division label="Chapter" delimiter=":"/>
          <division label="Verse"/>
        </divisions>
        <manuscripts>
          <ms abbrev="A" language="Greek" show="yes"><name>Witness A</name></ms>
        </manuscripts>
        <text><div number="Reuben">{inside_testament}</div></text>
      </version>
    </book>'''.encode("utf-8")


@pytest.mark.parametrize(
    ("inner", "expected"),
    [
        (
            '<div number="Title">' + _unit("1", "TITULUS") + '</div>'
            '<div number="1"><div number="1">' + _unit("2", "ALPHA") + '</div></div>',
            {
                ("Reuben", "Title"): ("TITULUS", "Reuben Title"),
                ("Reuben 1", "1"): ("ALPHA", "Reuben 1:1"),
            },
        ),
        (
            '<div number="1">' + _unit("1", "PREFACE")
            + '<div number="1">' + _unit("2", "VERSE") + '</div></div>',
            {
                ("Reuben", "1"): ("PREFACE", "Reuben 1"),
                ("Reuben 1", "1"): ("VERSE", "Reuben 1:1"),
            },
        ),
        (
            '<div number="Title">' + _unit("1", "TITULUS") + '</div>'
            '<div number="Subtitle">' + _unit("2", "SUBTITULUS") + '</div>'
            '<div number="1"><div number="1">' + _unit("3", "ALPHA") + '</div></div>',
            {
                ("Reuben", "Title"): ("TITULUS", "Reuben Title"),
                ("Reuben", "Subtitle"): ("SUBTITULUS", "Reuben Subtitle"),
                ("Reuben 1", "1"): ("ALPHA", "Reuben 1:1"),
            },
        ),
    ],
)
def test_shallow_textual_source_leaves_get_nonoverlapping_three_level_tf_sections(
    tmp_path: Path, inner, expected
):
    raw = _source(inner)
    parsed = parse_bytes(raw, source_path="Depth.xml")
    assert parsed.versions[0].divisions[0].label == "Testament"
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "Depth.xml").write_bytes(raw)
    books, warnings = load_source_directory(docs)
    assert not warnings

    data = build_tf_data(books)
    assert _section_coverage_ok(data), "every real word must have exactly one book/chapter/verse"
    report = build_conversion_report(docs, books, data)
    assert report["status"] == "ok", report["failed_checks"]
    assert report["source"]["readings"] == report["graph"]["readings"]

    out = tmp_path / "tf"
    assert write_tf(data, out)
    api = Fabric(locations=[str(out)], modules=[""], silent="deep").load(
        "source_ref", silent="deep"
    )
    assert api is not None
    assert tuple(api.T.sectionTypes) == ("book", "chapter", "verse")
    for (chapter, verse), (surface, original_ref) in expected.items():
        section = ("Depth", chapter, verse)
        node = api.T.nodeFromSection(section)
        assert node is not None, section
        assert api.T.sectionFromNode(node) == section
        assert api.T.text(node).strip() == surface
        assert api.F.source_ref.v(node) == original_ref

    assert len(tuple(api.F.otype.s("chapter"))) == len({p[0] for p in expected})
    assert len(tuple(api.F.otype.s("verse"))) == len(expected)
