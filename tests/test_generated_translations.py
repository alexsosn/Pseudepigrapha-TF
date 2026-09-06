from __future__ import annotations

from pseudepigrapha_tf.conversion import build_tf_data
from pseudepigrapha_tf.parser import InvalidSourceError, parse_bytes


def _version(
    *,
    title: str,
    language: str,
    manuscript: str,
    units: tuple[tuple[str, str, str], ...],
    generated: bool = False,
) -> str:
    marker = "OCP-Trans" if generated else manuscript
    prefix = "en_" if generated and language == "English" else "fr_" if generated and language == "French" else ""
    by_chapter: dict[str, list[tuple[str, str, str]]] = {}
    for chapter, unit_id, text in units:
        by_chapter.setdefault(chapter, []).append((chapter, unit_id, text))
    divs = []
    for chapter, rows in by_chapter.items():
        rendered = "".join(
            f'<unit id="{prefix}{unit_id}"><reading option="0" mss="{marker} ">{text}</reading></unit>'
            for _, unit_id, text in rows
        )
        divs.append(f'<div number="{chapter}"><div number="1">{rendered}</div></div>')
    return f'''
  <version title="{title}" author="Editor" language="{language}">
    <divisions>
      <division label="Chapter" delimiter=":"/>
      <division label="Verse"/>
    </divisions>
    <manuscripts>
      <ms abbrev="{marker}" language="{language}" show="yes"><name>{marker}</name></ms>
    </manuscripts>
    <text>{''.join(divs)}</text>
  </version>
'''


def _book(*versions: str) -> bytes:
    return (
        '<?xml version="1.0"?>\n<book filename="Demo" title="Demo">\n'
        + "".join(versions)
        + "\n</book>\n"
    ).encode("utf-8")


def _nodes(data, kind: str) -> list[int]:
    return [node for node, value in data.node_features["otype"].items() if value == kind]


def test_parser_preserves_generated_translation_without_misclassifying_genuine_english() -> None:
    book = parse_bytes(
        _book(
            _version(
                title="Greek",
                language="Greek",
                manuscript="G",
                units=(("1", "1", "alpha"),),
            ),
            _version(
                title="English scholarly edition",
                language="English",
                manuscript="E",
                units=(("2", "9", "scholarly"),),
            ),
            _version(
                title="Greek (French)",
                language="French",
                manuscript="ignored",
                units=(("1", "1", "traduction"),),
                generated=True,
            ),
        ),
        source_path="Demo.xml",
    )

    assert [version.title for version in book.versions] == ["Greek", "English scholarly edition"]
    assert len(book.generated_translations) == 1
    generated = book.generated_translations[0]
    assert generated.version.title == "Greek (French)"
    assert generated.target_language == "French"
    assert generated.marker == "OCP-Trans"
    assert generated.source_version_index == 0
    assert generated.source_version_title == "Greek"
    assert generated.generation_method == "llm"
    assert generated.generation_model == "openrouter/google/gemini-3.7-flash"


def test_generated_translation_keeps_existing_source_book_id_and_adds_explicit_version_edge() -> None:
    book = parse_bytes(
        _book(
            _version(
                title="Greek",
                language="Greek",
                manuscript="G",
                units=(("1", "1", "alpha"),),
            ),
            _version(
                title="Greek (English)",
                language="English",
                manuscript="ignored",
                units=(("1", "1", "translation"),),
                generated=True,
            ),
        ),
        source_path="Demo.xml",
    )
    data = build_tf_data([book])

    book_nodes = _nodes(data, "book")
    source = next(node for node in book_nodes if data.node_features["version_kind"][node] == "source")
    generated = next(
        node for node in book_nodes if data.node_features["version_kind"][node] == "generated_translation"
    )

    assert data.node_features["book"][source] == "Demo"
    assert data.node_features["book"][generated] == "Demo__translation__English"
    assert data.edge_features["translation_of"][generated] == {source}
    assert data.node_features["generation_marker"][generated] == "OCP-Trans"
    assert data.node_features["generation_method"][generated] == "llm"
    assert data.node_features["generation_model"][generated] == "openrouter/google/gemini-3.7-flash"

    synthetic = next(
        node
        for node in _nodes(data, "manuscript")
        if data.node_features.get("ms_abbrev", {}).get(node) == "OCP-Trans"
    )
    assert data.node_features["synthetic_witness"][synthetic] == 1


def test_unit_alignment_uses_structural_identity_and_occurrence_not_position_or_bare_id() -> None:
    book = parse_bytes(
        _book(
            _version(
                title="Greek",
                language="Greek",
                manuscript="G",
                units=(
                    ("1", "7", "source-first"),
                    ("1", "7", "source-second"),
                    ("2", "8", "source-third"),
                ),
            ),
            _version(
                title="Greek (French)",
                language="French",
                manuscript="ignored",
                units=(
                    ("2", "8", "translated-third"),
                    ("1", "7", "translated-first"),
                    ("1", "7", "translated-second"),
                ),
                generated=True,
            ),
        ),
        source_path="Demo.xml",
    )
    data = build_tf_data([book])

    units = _nodes(data, "unit")
    source_units = [node for node in units if data.node_features["version_kind"][node] == "source"]
    generated_units = [
        node for node in units if data.node_features["version_kind"][node] == "generated_translation"
    ]
    source_by_ref_and_index = {
        (data.node_features["source_ref"][node], data.node_features["unit_index"][node]): node
        for node in source_units
    }
    generated_by_ref_and_index = {
        (data.node_features["source_ref"][node], data.node_features["unit_index"][node]): node
        for node in generated_units
    }

    # Generated sequence starts with source chapter 2, so positional zip would be wrong.
    assert data.edge_features["translation_unit_of"][generated_by_ref_and_index[("2:1", 1)]] == {
        source_by_ref_and_index[("2:1", 3)]
    }

    # Two identical (path,id) identities remain two distinct occurrence-aligned edges.
    first_duplicate = generated_by_ref_and_index[("1:1", 2)]
    second_duplicate = generated_by_ref_and_index[("1:1", 3)]
    assert data.edge_features["translation_unit_of"][first_duplicate] == {
        source_by_ref_and_index[("1:1", 1)]
    }
    assert data.edge_features["translation_unit_of"][second_duplicate] == {
        source_by_ref_and_index[("1:1", 2)]
    }


def test_unmatched_generated_translation_fails_closed() -> None:
    data = _book(
        _version(
            title="Greek",
            language="Greek",
            manuscript="G",
            units=(("1", "1", "source"),),
        ),
        _version(
            title="Unmatched (French)",
            language="French",
            manuscript="ignored",
            units=(("9", "999", "translation"),),
            generated=True,
        ),
    )

    try:
        parse_bytes(data, source_path="Demo.xml")
    except InvalidSourceError as exc:
        assert "generated translation" in str(exc)
        assert "Unmatched (French)" in str(exc)
        assert "source version" in str(exc)
    else:
        raise AssertionError("unmatched generated translation was accepted")


def test_translation_helper_is_public_api() -> None:
    from pseudepigrapha_tf import Translations

    assert Translations.__name__ == "Translations"
